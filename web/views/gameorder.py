from datetime import datetime
from django.conf import settings
from django import forms
from django.db.models import Q
from django.shortcuts import render, redirect, HttpResponse
from utils.media_path import get_upload_path
from utils.pager import Pagination
from utils.qr_code_to_link import qr_code_to_link
from utils.response import BaseResponse
from utils.time_filter import filter_by_date_range
from web import models
from django.contrib import messages
from django.contrib.messages.api import get_messages
from web.models import GameOrder, GameDenomination, TransactionRecord,UserInfo
from decimal import Decimal, getcontext
from django.db.models import Case, When, Value, IntegerField, F
from itertools import combinations
import logging

logger = logging.getLogger('web')

def gameorder_list(request):
    keyword = request.GET.get('keyword', '').strip()
    usertype = request.userdict.usertype

    # 基础查询集
    if usertype == 'CUSTOMER':
        queryset = models.GameOrder.objects.filter(consumer=request.userinfo, active=1).all()
    else:
        queryset = models.GameOrder.objects.filter(active=1).select_related('consumer__level').annotate(
            user_discount_percent=F('consumer__level__percent'),
            is_creator=Case(
                When(created_by=request.userinfo, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            )
        ).order_by('-is_creator', 'user_discount_percent', '-id')

    # 关键字查询
    con = Q()
    if keyword:
        con.connector = 'OR'
        con.children.append(('consumer__username__contains', keyword))
        con.children.append(('order_number__contains', keyword))
        queryset = queryset.filter(con)

    # 日期过滤
    queryset, start_date, end_date, pager = filter_by_date_range(request, queryset)

    # 初始化qb_results为空列表
    qb_results = []

    # 处理应用方案逻辑
    applied_orders = request.GET.get('applied_orders')
    if applied_orders:
        # 分割订单号并过滤主查询集
        applied_order_list = applied_orders.split(',')
        queryset = queryset.filter(order_number__in=applied_order_list)

        try:
            # 获取这些订单的详细信息
            applied_orders_data = []
            for order in queryset:
                applied_orders_data.append({
                    'id': order.id,
                    'amount': Decimal(str(order.recharge_option.amount)),
                    'discount': Decimal(str(order.consumer.level.percent)) / Decimal('100'),
                    'order_number': order.order_number,
                    'consumer_admin': order.consumer.parent if order.consumer.parent else None,
                })

            # 直接构建单个结果
            if applied_orders_data:
                qb_target = sum(o['amount'] for o in applied_orders_data)
                result = find_qb_combinations(
                    request=request,
                    orders=applied_orders_data,
                    qb_target=qb_target,
                    qb_discount=Decimal(request.GET.get('qb_discount', '75')) / 100,
                    max_combine=len(applied_orders_data)
                )
                qb_results = result[:1] if result else []

        except Exception as e:
            logger.error(f"构建应用方案出错: {e}")

    # 正常QB匹配逻辑
    elif request.GET.get('qb_target'):
        try:
            qb_target = Decimal(request.GET.get('qb_target'))
            qb_discount = Decimal(request.GET.get('qb_discount', '75')) / Decimal('100')
            max_combine = int(request.GET.get('max_combine', '4'))

            valid_orders = queryset.filter(
                recharge_option__isnull=False,
                consumer__level__percent__gt=qb_discount * 100
            ).select_related('recharge_option', 'consumer__level')

            orders = [
                {
                    'id': o.id,
                    'amount': Decimal(str(o.recharge_option.amount)),
                    'discount': Decimal(str(o.consumer.level.percent)) / Decimal('100'),
                    'order_number': o.order_number,
                    'consumer_admin': o.consumer.parent if o.consumer.parent else None,
                }
                for o in valid_orders
            ]

            qb_results = find_qb_combinations(
                request=request,
                orders=orders,
                qb_target=qb_target,
                qb_discount=qb_discount,
                max_combine=max_combine
            )

        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"QB匹配错误: {e}")
            qb_results = []

    # 分页处理
    pager = Pagination(request, queryset)

    # 准备清除应用方案的链接参数
    cleaned_query = request.GET.copy()
    if 'applied_orders' in cleaned_query:
        del cleaned_query['applied_orders']

    context = {
        # 最重要的两个数据，分别用于订单循环和命中查询循环
        'pager': pager,
        'qb_results': qb_results,  # 现在这个变量总是有定义

        'keyword': keyword,
        'qb_target': request.GET.get('qb_target'),
        'qb_discount': request.GET.get('qb_discount', '75'),
        'max_combine': request.GET.get('max_combine', '4'),
        'end_date': end_date,
        'date_field': request.GET.get('date_field', ''),
        'tolerance': request.GET.get('tolerance', '10'),
        'applied_orders': applied_orders,
        'cleaned_query': cleaned_query.urlencode(),
    }
    return render(request, 'gameorder_list.html', context)


def find_qb_combinations(request, qb_target, orders, qb_discount, max_combine=4):
    qb_target = Decimal(str(qb_target))
    qb_discount = Decimal(str(qb_discount))
    max_combine = int(str(max_combine))

    # 获取精度范围参数，默认为10
    try:
        tolerance = Decimal(request.GET.get('tolerance', '10'))
    except:
        tolerance = Decimal('10')

    getcontext().prec = 8  # 设置Decimal精度

    all_results = []
    seen_combinations = set()  # 用于去重

    # 1. 查找所有符合条件的组合（精确匹配和近似匹配）
    for r in range(1, max_combine + 1):
        for combo in combinations(orders, r):
            total = sum(order['amount'] for order in combo)
            difference = abs(total - qb_target)

            # 只保留在精度范围内的组合
            if difference > tolerance:
                continue

            # 生成组合的唯一标识用于去重
            combo_key = tuple(sorted(order['id'] for order in combo))
            if combo_key in seen_combinations:
                continue
            seen_combinations.add(combo_key)

            # 构建结果
            result = build_single_combination(request, list(combo), qb_discount, qb_target)
            result['difference'] = float(difference)  # 添加差异值字段
            all_results.append(result)

    # 2. 如果没有找到任何匹配，尝试放宽条件（仅当tolerance>0时）
    if not all_results and tolerance > 0:
        # 查找最接近的1-2个组合
        closest_combinations = []
        for r in range(1, max_combine + 1):
            for combo in combinations(orders, r):
                total = sum(order['amount'] for order in combo)
                difference = abs(total - qb_target)

                if not closest_combinations or difference < closest_combinations[0]['difference']:
                    closest_combinations = [{
                        'combo': combo,
                        'difference': difference
                    }]
                elif difference == closest_combinations[0]['difference']:
                    closest_combinations.append({
                        'combo': combo,
                        'difference': difference
                    })

        # 添加最接近的组合（最多2个）
        for item in closest_combinations[:2]:
            combo_key = tuple(sorted(order['id'] for order in item['combo']))
            if combo_key not in seen_combinations:
                result = build_single_combination(request, list(item['combo']), qb_discount, qb_target)
                result['difference'] = float(item['difference'])
                all_results.append(result)
                seen_combinations.add(combo_key)

    # 3. 结果排序：先按差异值排序，再按组合大小排序
    all_results.sort(key=lambda x: (x['difference'], len(x['combination'])))

    return all_results


def build_single_combination(request, combo_orders, qb_discount, qb_target):
    """构建单个组合的详细信息"""
    qb_total = sum(order['amount'] for order in combo_orders)
    remaining = qb_target - qb_total
    difference = abs(remaining)

    # 计算财务数据
    income = sum(order['amount'] * order['discount'] for order in combo_orders)
    cost = qb_total * qb_discount
    service_fee = len(combo_orders) * Decimal(settings.SYS_FEE)
    total_fee, fee_details, report_text = calculate_fee(combo_orders, request.userinfo)
    profit = income - cost - service_fee - total_fee

    # 生成描述信息
    combo_str = " + ".join(f"{order['amount']}" for order in combo_orders)
    if remaining == 0:
        match_type = 'exact'
        desc = f"完美匹配组合：{combo_str} = {qb_total}QB"
    elif difference <= 10:  # 这里的10可以和前端的默认值保持一致
        match_type = 'near'
        desc = f"近似匹配组合：{combo_str} = {qb_total}QB (误差:{difference}QB)"
    else:
        match_type = 'boundary'
        desc = f"边界匹配组合：{combo_str} = {qb_total}QB (误差:{difference}QB)"

    return {
        'order_numbers_list': [order['order_number'] for order in combo_orders],  # 新增：单独列出订单号
        'order_details': [
            {
                'number': order['order_number'],
                'amount': int(order['amount']),  # 强制转换为整数
                'discount_percent': int(order['discount'] * 100),  # 新增预计算字段
                'consumer': order.get('consumer_username', '')
            }
            for order in combo_orders
        ],
        'order_numbers': [order['order_number'] for order in combo_orders],
        'qb_total': int(qb_total),  # 总QB转为整数
        'remaining': int(remaining),  # 剩余QB转为整数
        'difference': float(difference),  # 用于排序
        'income': round(income, 2),  # 合计金额保留2位小数
        'cost': cost,
        'profit': profit,
        'combination': [order['amount'] for order in combo_orders],
        'description': desc,
        'orders': [{
            'amount': int(o['amount']),
            'discount_percent': int(o['discount'] * 100),
            'final_price': o['amount'] * o['discount']
        } for o in combo_orders],
        'report_text': report_text,
        'efficiency': float(profit / qb_total) if qb_total else 0.0,
        'match_type': match_type,
        'service_fee': service_fee,
        'transfer_fee': total_fee
    }

def calculate_fee(combo_orders, current_user):
    """
    combo_orders:某个方案中的订单组合列表
    """
    system_fee_per_order = Decimal(settings.SYS_FEE)  # 系统费
    external_fee_per_order = Decimal(settings.THIRD_FEE)  # 三方系统订单借调费单价
    # fee_per_order = int(settings.THIRD_FEE)  int() 会直接截断小数部分，将 0.5 转换为 0
    external_orders = []
    internal_orders = []

    # combo_orders是符合方案的组合订单列表
    # 而order,是订单列表中一个，被依次遍历循环处理。这里的order，不是原始数据，是简化字典
    for order in combo_orders:
        order_amount = order['amount']
        discount = order['discount']
        # 这里的金额，是应该付款给点券订单用户的金额
        final_amount = order_amount * discount

        # 判断是否为内部订单
        # print('123:', order['consumer_admin'], type(order['consumer_admin']))
        # print('345:', current_user.username, type(current_user.username))
        # print('678:', current_user.parent, type(current_user.parent))
        # 以下是以上的输出，可以看出，注释的判断是否为内部订单的逻辑，是有问题的。
        # 123: root1 <class 'web.models.UserInfo'>
        # 345: root <class 'str'>
        # 678: None <class 'NoneType'>
        # is_internal = (
        #         order.get('consumer_admin') == current_user.username or
        #         order.get('consumer_admin') == getattr(current_user, 'parent', None)
        # )

        # 更健壮的内部订单判断逻辑
        # 获取当前订单的消费者的管理员
        consumer_admin = order.get('consumer_admin')
        is_internal = False

        # 情况1：consumer_admin 是当前用户自己
        # 如果当前订单的消费者的管理员，就是当前登录系统的用户，即出库用户  一家人，圈内人
        if str(consumer_admin) == str(current_user.username):
            is_internal = True

        # 情况2：consumer_admin 是当前用户的上级
        # 如果当前登录用户，即出库用户，有父级，即是被管理员创建的  并且，其创建者，与当前订单的消费者的创建者是同一个人
        elif hasattr(current_user, 'parent') and str(consumer_admin) == str(current_user.parent):
            is_internal = True

        # 情况3：当前用户是 consumer_admin 的上级（如果需要）
        # 根据你的业务逻辑决定是否添加这个条件

        # 如果当前订单是内部的
        if is_internal:
            # 将当前订单的订单号，充值面额,订单消费者的管理员作为字典中的三条数据，打包添加到内部订单列表中
            internal_orders.append({
                'order_number': order['order_number'],
                'amount': final_amount,
                'admin': order['consumer_admin']
            })
        else:
            # 否则，将当前订单的订单号，充值面额，订单消费者的创建者，出库人所在圈子的创建者，此订单的三方借调费用，时间戳作为字典，添加到外部订单列表中
            external_orders.append({
                'order_number': order['order_number'],
                'amount': final_amount,
                'source_admin': order['consumer_admin'],  # 订单入库人所在圈子的管理员
                'target_admin': current_user.username,  # 订单出库人所在圈子的管理员
                'fee': external_fee_per_order,  # 每单的借调费
                'timestamp': datetime.now().isoformat()
            })

    # 计算总的第三方订单借调费用
    external_total_fee = sum(item['fee'] for item in external_orders)

    # 计算总的第三方订单借调费用
    system_total_fee = system_fee_per_order * len(combo_orders)

    # 生成详细文案
    report_text = generate_fee_report(internal_orders, external_orders, combo_orders)

    return external_total_fee, system_total_fee , report_text


def generate_fee_report(internal_orders, external_orders, combo_orders):
    """生成易读的费用报告文案"""
    internal_fee_summary = []
    external_fee_summary = []
    system_fee_summary = []

    if internal_orders:
        system_fee_summary.append("\n【内部订单明细】")
        line = f"该方案共计{len(internal_orders)}内部单，这些订单无三方费用，仅有系统费."
        system_fee_summary.append(line)
    internal_fee_summary_to_string = "".join(internal_fee_summary)

    # 添加第三方订单详情
    if external_orders:
        external_fee_summary.append("\n【第三方订单费用明细】")
        for item in external_orders:
            line = (f"订单号{item['order_number']}的订单是{item['source_admin']}管理员所属，"
                    f"需要支付第三方借调费 {item['fee']}元，"
                    f"{item['source_admin']} 管理员需向你转账金额 {item['amount']}")
            external_fee_summary.append(line)
    external_summary_to_string = "".join(external_fee_summary)

    #
    if combo_orders:
        system_fee_summary.append("\n【系统费明细】")
        line = f"该方案共计{len(combo_orders)}单，故而，系统费总额为{len(combo_orders)}*{settings.SYS_FEE}元."
        system_fee_summary.append(line)
    system_fee_summary_to_string = "".join(system_fee_summary)


    return internal_fee_summary_to_string+external_summary_to_string+system_fee_summary_to_string


class BootStrapForm:
    exclude_filed_list = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # {'title':对象,"percent":对象}
        for name, field in self.fields.items():
            if name in self.exclude_filed_list:
                continue
            field.widget.attrs['class'] = "form-control"
            field.widget.attrs['placeholder'] = "请输入{}".format(field.label)




class GameOrderAddModelForm(BootStrapForm, forms.ModelForm):
    class Meta:
        model = GameOrder
        fields = ['platform','QV', 'game', 'recharge_option', 'recharge_link', 'qr_code', 'consumer']

    def __init__(self,  *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.fields['recharge_link'].required = False
        self.fields['qr_code'].required = False
        # 初始化时设置空的recharge_option queryset
        self.fields['recharge_option'].queryset = GameDenomination.objects.none()
        if self.request.userinfo.usertype == 'ADMIN':
            self.fields['consumer'].queryset = UserInfo.objects.filter(parent__username=self.request.userinfo.username).filter(active=1).all()
        else:
            self.fields['consumer'].queryset = UserInfo.objects.filter()
        # 如果有初始数据，设置对应的选项
        if 'game' in self.data and 'platform' in self.data:
            try:
                game_id = int(self.data.get('game'))
                platform = self.data.get('platform')
                self.fields['recharge_option'].queryset = GameDenomination.objects.filter(
                    game_id=game_id,
                    platform=platform,
                    active=True
                ).order_by('amount')
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.game:
            # 使用默认的反向关系名称 gamedenomination_set
            # 或者如果您已经添加了 related_name='order_options'，可以保持原样
            self.fields['recharge_option'].queryset = GameDenomination.objects.filter(
                game=self.instance.game,
                platform=self.instance.platform,
                active=True
            ).order_by('amount')


def gameorder_add(request):
    if request.method == 'GET':
        form = GameOrderAddModelForm(request=request)
        return render(request, 'gameorder_form.html', {'form': form})

    form = GameOrderAddModelForm(request=request,data=request.POST, files=request.FILES)

    if not form.is_valid():
        print('1')
        return render(request, 'gameorder_form.html', {'form': form})

    # 获取用户名 - 根据你的实际用户模型调整
    username = request.userdict.username

    # 处理二维码上传
    if request.POST.get('recharge_method') == 'qrcode':
        qr_code_file = form.cleaned_data['qr_code']

        try:
            # 获取存储路径
            # qr_code_path = get_upload_path(qr_code_file,username)
            # # full_path = os.path.join(settings.MEDIA_ROOT, qr_code_path)
            # full_path = os.path.join(settings.MEDIA_ROOT, qr_code_path)
            qr_code_path, full_path = get_upload_path(qr_code_file, username)

            # 保存文件
            with open(full_path, 'wb+') as destination:
                for chunk in qr_code_file.chunks():
                    destination.write(chunk)

            # 解析二维码
            qr_link = qr_code_to_link(full_path)
            if not qr_link:
                form.add_error('consumer', '无法解析二维码内容')
                print('2')
                return render(request, 'gameorder_form.html', {'form': form})

            # 更新表单数据
            form.instance.recharge_link = qr_link
            form.instance.qr_code = qr_code_path

        except Exception as e:
            form.add_error('consumer', f'文件处理出错: {str(e)}')
            print(e)
            return render(request, 'gameorder_form.html', {'form': form})

    # 保存订单
    order = form.save(commit=False)
    order.created_by = request.userinfo  # 或 request.userinfo
    order.save()

    messages.success(request, '订单创建成功')
    return redirect('gameorder_list')



from django.http import JsonResponse
from web.models import GameDenomination


def gameorder_load_charge_options(request):
    game_id = request.GET.get('game')
    platform = request.GET.get('platform')

    if not game_id or not platform:
        return JsonResponse({'status': False, 'error': '缺少参数'}, status=400)

    try:
        options = GameDenomination.objects.filter(
            game_id=game_id,
            platform=platform,
            active=True
        ).order_by('amount')

        option_list = [
            {
                'id': obj.id,
                'display_text': f"{obj.amount}元(总{obj.total_currency}点券: {obj.base_currency}基础+{obj.gift_currency}赠送+{obj.bonus_currency}绑定)"
            }
            for obj in options
        ]

        return JsonResponse({'status': True, 'options': option_list})

    except Exception as e:
        return JsonResponse({'status': False, 'error': str(e)}, status=500)

from django.forms.models import model_to_dict
from django.forms.models import model_to_dict
from django.shortcuts import render, redirect
from django.contrib import messages
from web.models import GameOrder, OrderEditLog
# from web.forms import GameOrderAddModelForm


def gameorder_edit(request, pk):
    try:
        order = GameOrder.objects.get(pk=pk, active=1)
    except GameOrder.DoesNotExist:
        messages.error(request, '订单不存在或已被删除')
        return redirect('gameorder_list')

    # 保存原始数据 - 确保获取的是可序列化的值
    original_data = model_to_dict(order)

    # 特殊处理可能包含对象的字段
    if hasattr(order, 'recharge_option') and order.recharge_option:
        original_data['recharge_option'] = order.recharge_option.id  # 存储ID而不是对象

    if request.method == 'GET':
        form = GameOrderAddModelForm(instance=order,request=request)
        return render(request, 'gameorder_form.html', {'form': form, 'is_edit': True})

    form = GameOrderAddModelForm(data=request.POST, files=request.FILES, instance=order,request=request)

    if not form.is_valid():
        return render(request, 'gameorder_form.html', {'form': form, 'is_edit': True})

    # Handle QR code upload if recharge method is qrcode
    if request.POST.get('recharge_method') == 'qrcode':
        qr_code_file = form.cleaned_data.get('qr_code')

        if qr_code_file:  # Only process if a new QR code was uploaded
            username = request.userdict.username

            try:
                # Get upload path and save file
                qr_code_path, full_path = get_upload_path(qr_code_file, username)

                with open(full_path, 'wb+') as destination:
                    for chunk in qr_code_file.chunks():
                        destination.write(chunk)

                # Parse QR code
                qr_link = qr_code_to_link(full_path)
                if not qr_link:
                    form.add_error('consumer', '无法解析二维码内容')
                    return render(request, 'gameorder_form.html', {'form': form, 'is_edit': True})

                # Update form data
                form.instance.recharge_link = qr_link
                form.instance.qr_code = qr_code_path

            except Exception as e:
                form.add_error('consumer', f'文件处理出错: {str(e)}')
                return render(request, 'gameorder_form.html', {'form': form, 'is_edit': True})
        else:
            # If no new QR code was uploaded but method is qrcode, keep existing values
            if order.qr_code:
                form.instance.qr_code = order.qr_code
            if order.recharge_link:
                form.instance.recharge_link = order.recharge_link

    # 获取变更的字段并确保值可序列化
    changed_fields = {}
    for field in form.changed_data:
        old_value = original_data.get(field)
        new_value = form.cleaned_data.get(field)

        # 特殊处理recharge_option字段
        if field == 'recharge_option' and new_value:
            new_value = {
                'id': new_value.id,
                'display': str(new_value),  # 使用对象的字符串表示
                # 可以添加其他需要的属性
            }
            if old_value and hasattr(old_value, 'id'):
                old_value = {
                    'id': old_value.id,
                    'display': str(old_value),
                }

        # 处理ImageField/FileField
        elif hasattr(new_value, 'name'):  # 处理文件字段
            new_value = new_value.name if new_value else None
            if old_value and hasattr(old_value, 'name'):
                old_value = old_value.name

        changed_fields[field] = {
            'old': old_value,
            'new': new_value
        }

    # Save the order
    order = form.save(commit=False)
    order.save()

    # 记录修改日志
    OrderEditLog.objects.create(
        order=order,
        operator=request.userinfo,
        action='update',
        changed_fields=changed_fields,
        ip_address=request.META.get('REMOTE_ADDR')
    )

    messages.success(request, '订单更新成功')
    return redirect('gameorder_list')

def gameorder_delete(request):
    """
    删除游戏订单（软删除，设置active=0）
    请求参数：
    - oid: 订单ID
    """
    cid = request.GET.get('cid', 0)

    # 验证订单ID是否存在
    if not cid:
        res = BaseResponse(status=False, detail="请选择要删除的订单")
        return JsonResponse(res.dict)

    try:
        # 检查订单是否存在且是激活状态
        exists = models.GameOrder.objects.filter(id=cid, active=1).exists()
        if not exists:
            res = BaseResponse(status=False, detail="要删除的订单不存在或已被删除")
            return JsonResponse(res.dict)

        # 执行软删除（设置active=0）
        models.GameOrder.objects.filter(id=cid).update(active=0)

        # 可以在这里添加相关的交易记录（如果需要）
        # 例如记录删除操作到TransactionRecord

        res = BaseResponse(status=True, detail="订单删除成功")
        return JsonResponse(res.dict)

    except Exception as e:
        res = BaseResponse(status=False, detail=f"删除订单时出错: {str(e)}")
        return JsonResponse(res.dict)


from django import forms
from web.models import OrderEditLog


class OrderEditLogForm(forms.ModelForm):
    class Meta:
        model = OrderEditLog
        fields = ['action', 'changed_fields']  # 使用模型中的实际字段名
        widgets = {
            'action': forms.Select(attrs={
                'class': 'form-control'
            }),
            'changed_fields': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': '请输入变更说明...'
            })
        }

def gameorder_edit_log(request, pk):
    """查看订单修改记录（只读）"""
    try:
        order = GameOrder.objects.get(id=pk, active=1)
    except GameOrder.DoesNotExist:
        messages.error(request, '订单不存在或已被删除')
        return redirect('gameorder_list')

    logs = order.edit_logs.all().order_by('-operation_time')

    context = {
        'order': order,
        'logs': logs,
    }
    return render(request, 'gameorder_edit_log.html', context)