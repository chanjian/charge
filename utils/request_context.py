from datetime import datetime
from django.conf import settings
from django import forms
from django.db.models import Q
from django.shortcuts import render, redirect ,HttpResponse
from utils.media_path import get_upload_path
from utils.pager import Pagination
from utils.qr_code_to_link import qr_code_to_link
from utils.response import BaseResponse
from utils.time_filter import filter_by_date_range
from web import models
from django.contrib import messages
from django.contrib.messages.api import get_messages
from web.models import GameOrder,GameDenomination,TransactionRecord

import logging
logger = logging.getLogger('web')


def gameorder_list(request):
    messages = get_messages(request)
    for msg in messages:
        print(msg)

    keyword = request.GET.get('keyword', '').strip()
    usertype = request.userdict.usertype

    # 如果时是消费者，查询消费者是当前消费者的所有订单
    if usertype == 'CUSTOMER':
        queryset = models.GameOrder.objects.filter(consumer=request.userinfo, active=1).all()
    # 否则，查询所有获取所有活跃的 GameOrder 记录，并为每条记录添加两个额外信息
    # 1.关联消费者的等级折扣百分比
    # 2.标记当前请求用户是否是订单的创建者(1表示是，0表示不是)
    else:
        from django.db.models import F, Case, When, Value, IntegerField
        # 一次性加载 consumer 和 consumer.level
        # consumer__level 被预加载，后续访问 consumer.level 或 consumer__level__percent 不会触发新查询
        queryset = models.GameOrder.objects.filter(active=1).select_related('consumer__level'
        ).annotate(
            user_discount_percent=models.F('consumer__level__percent'),  # 获取用户等级对应的折扣百分比
            is_creator=Case(
                When(created_by=request.userinfo, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            )
        ).order_by(
            '-is_creator',  # 当前用户创建的订单优先
            'user_discount_percent',  # 折扣百分比小的排前面（折扣更大）
            '-id'  # 最后按ID降序作为次要排序条件
        )

    #关键字查询
    con = Q()
    if keyword:
        con.connector = 'OR'
        con.children.append(('consumer__username__contains', keyword))
        con.children.append(('order_number__contains', keyword))
        queryset = queryset.filter(con)

    # 调用封装好的函数进行日期过滤
    queryset, start_date, end_date, pager = filter_by_date_range(request, queryset)

    pager = Pagination(request,queryset)

    # QB匹配功能
    qb_results = []
    qb_target = request.GET.get('qb_target')

    if qb_target:
        try:
            # 获取并验证参数
            qb_target = Decimal(qb_target)
            qb_discount = Decimal(request.GET.get('qb_discount', '75')) / Decimal('100')
            max_combine = int(request.GET.get('max_combine', '4'))

            # 获取有效订单（折扣>用户设置的折扣）
            # 在上面的查询条件的基础上再增加过滤条件进行查询过滤
            valid_orders = queryset.filter(
                recharge_option__isnull=False, # 必须关联了充值选项
                consumer__level__percent__gt=qb_discount*100 # 用户等级折扣必须大于给QB用户的报价折扣
            ).select_related('recharge_option', 'consumer__level')

            # 构建订单列表，每个订单包含id、金额和折扣
            # 简化字典，只存储必要的个字段，内存占用更小，对于大规模订单列表(如10万+条)优势明显
            # 相较于完整的对象，完整的对象内存消耗可能要高出这种简化字典的3-5倍
            orders = [
                {
                    # 核心计算字段
                    'id': o.id,
                    'amount': Decimal(str(o.recharge_option.amount)),
                    'discount': Decimal(str(o.consumer.level.percent)) / Decimal('100'),
                     # 新增审计字段
                    'order_number': o.order_number,  # 订单号
                    'consumer_admin': o.consumer.created_by.username if o.consumer.created_by else None,  # 消费者管理员
                }
                for o in valid_orders
            ]

            # 查找最佳组合
            qb_results = find_qb_combinations(
                request=request,
                target_qb=qb_target,
                orders=orders,
                client_discount=qb_discount,
                max_combine=max_combine
            )

        except (ValueError, TypeError, AttributeError) as e:
            print(f"QB匹配错误: {e}")

    context = {
        'pager':pager,
        'keyword':keyword,
        'qb_target': qb_target,  # 当前QB目标值
        'qb_discount': request.GET.get('qb_discount', '75'),  # 当前折扣设置
        'max_combine': request.GET.get('max_combine', '4'),  # 当前组合数设置
        'qb_results': qb_results,  # QB匹配结果
        'start_date': start_date,  # 日期筛选相关
        'end_date': end_date,
        'date_field': request.GET.get('date_field', ''),  # 保留日期字段参数
    }
    return render(request, 'gameorder_list.html', context)
    # return render(request, 'gameorder_list.html', locals())


from itertools import combinations


def find_qb_combinations(request,target_qb, orders, client_discount, max_combine=4):
    target_qb = Decimal(str(target_qb))
    client_discount = Decimal(str(client_discount))
    results = []
    best_left = None
    best_right = None
    exact_match = None

    # 检查精确匹配
    # 这段代码的作用是 在订单列表 orders 中寻找一个组合，使得该组合的订单金额之和精确等于目标值 target_qb
    # r 表示当前尝试的组合大小（即选取 r 个订单进行组合）
    # max_combine 是允许的最大组合订单数（例如最多尝试 3 个订单的组合）
    # 从 r=1（单订单）开始，逐步增加组合大小，直到 r=max_combine
    # +1 是为了确保循环能覆盖到 max_combine 本身，在 Python 的 range(start, stop) 函数中，stop 参数是 不包含在范围内的
    for r in range(1, max_combine + 1):
        # combinations(orders, r) 是 Python itertools 模块提供的函数，用于生成 orders 中所有长度为 r 的可能组合（不重复、顺序无关）
        # 例如，若 orders = [A, B, C]，则：
        # r=1 → 组合为 [A], [B], [C]
        # r=2 → 组合为 [A, B], [A, C], [B, C]
        # r=3 → 组合为 [A, B, C]
        for combo in combinations(orders, r):
            # 对每个组合 combo，计算其中所有订单的 amount 字段之和
            # combo 是 tuple 类型，即使只有一个元素也会显示为 (order,)
            total = sum(order['amount'] for order in combo)
            if total == target_qb:
                exact_match = combo
                break
        if exact_match:
            break

    if exact_match:
        # 如果找到一个精确匹配的组合（exact_match），则将该组合格式化后返回（包装成列表）
        return [build_combination(request,exact_match, client_discount, target_qb)]

    # 寻找最近邻组合
    for r in range(1, max_combine + 1):
        for combo in combinations(orders, r):
            total = sum(order['amount'] for order in combo)

            # 左边界（总QB <= 目标）
            if total <= target_qb:
                if not best_left or (target_qb - total) < (target_qb - best_left['total_qb']):
                    current = build_combination(combo, client_discount, target_qb)
                    best_left = current

            # 右边界（总QB >= 目标）
            if total >= target_qb:
                if not best_right or (total - target_qb) < (best_right['total_qb'] - target_qb):
                    current = build_combination(combo, client_discount, target_qb)
                    best_right = current

    # 收集结果并排序
    if best_left:
        results.append(best_left)
    if best_right and best_right != best_left:
        results.append(best_right)

    results.sort(key=lambda x: abs(x['remaining']))
    return results


from decimal import Decimal, getcontext


def build_combination(request,combo_orders, client_discount, target_qb):

    # 查询后的组合所有订单的QB总额，也是档位金额总额
    total_qb = sum(order['amount'] for order in combo_orders)
    remaining = target_qb - total_qb

    # 点券订单的客户需要被扣款的金额，也就是我的进账
    income = sum(order['amount'] * order['discount'] for order in combo_orders)
    # QB订单的客户需要支付给他的金额，也就是我的出项
    cost = total_qb * client_discount

    service_fee = len(combo_orders) * Decimal(settings.SYS_FEE)
    total_fee, fee_details, report_text = calculate_transfer_fee_with_logging(combo_orders, request.userinfo)
    transfer_fee = total_fee

    # 我的利润 = 进账 - 出账 - 系统服务费 - 第三方订单借调费
    profit = income - cost - service_fee - transfer_fee

    combo_str = " + ".join(f"{order['amount']}" for order in combo_orders)
    description = (
        f"组合：{combo_str}\n"
        f"总QB：{total_qb}，剩余：{remaining if remaining > 0 else -remaining}\n"
        f"成本：{cost:.2f}元，利润：{profit:.2f}元"
    )

    return {
        'order_ids': [order['id'] for order in combo_orders],
        'total_qb': total_qb,
        'remaining': remaining,
        'income': income,
        'cost': cost,
        'profit': profit,
        'description': description,
        'combination': [order['amount'] for order in combo_orders],
        # 'report_text':report_text,
    }


def calculate_transfer_fee_with_logging(combo_orders, current_user):
    #三方系统订单借调费单价
    fee_per_order = int(settings.THIRD_FEE)
    fee_details = []
    internal_orders = []

    for order in combo_orders:
        order_amount = order['amount']
        discount = order['discount']
        final_amount = order_amount * discount

        # 判断是否为内部订单
        is_internal = (
                order.get('consumer_admin') == current_user.username or
                order.get('consumer_admin') == getattr(current_user.created_by, 'username', None)
        )

        if is_internal:
            internal_orders.append({
                'order_number': order['order_number'],
                'amount': final_amount,
                'admin': order['consumer_admin']
            })
        else:
            fee_details.append({
                'order_number': order['order_number'],
                'amount': final_amount,
                'source_admin': order['consumer_admin'],
                'target_admin': current_user.username,
                'fee': fee_per_order,
                'timestamp': datetime.now().isoformat()
            })

    # 计算总费用
    total_fee = sum(item['fee'] for item in fee_details)

    # 生成详细文案
    report_text = generate_fee_report(internal_orders, fee_details)

    return total_fee, fee_details, report_text


def generate_fee_report(internal_orders, fee_details):
    """生成易读的费用报告文案"""
    report_lines = []

    # 添加第三方订单详情
    if fee_details:
        report_lines.append("【第三方订单费用明细】")
        for item in fee_details:
            line = (f"订单 {item['order_number']} 是 {item['source_admin']} 管理员所属，"
                    f"需要支付第三方借调费 {item['fee']}，"
                    f"需转账金额 {item['amount']}")
            report_lines.append(line)

    # 添加内部订单详情
    if internal_orders:
        report_lines.append("\n【内部订单明细】")
        for item in internal_orders:
            line = f"订单 {item['order_number']} 是 {item['admin']} 管理员所属 (内部订单，免手续费)"
            report_lines.append(line)

    # 添加汇总信息
    if fee_details:
        total_fee = sum(item['fee'] for item in fee_details)
        total_amount = sum(item['amount'] for item in fee_details)
        report_lines.append(
            f"\n总计：{len(fee_details)} 笔第三方订单，"
            f"总手续费 {total_fee}，"
            f"总转账金额 {total_amount}"
        )

    return "\n".join(report_lines)


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

# class GameOrderAddModelForm(BootStrapForm,forms.ModelForm):
#     class Meta:
#         model = GameOrder
#         fields = ['platform', 'game_name', 'recharge_option', 'custom_amount', 'recharge_link', 'qr_code', 'consumer']
#
#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         platform = self.initial.get('platform') or self.data.get('platform')
#
#         if platform == 'IOS':
#             # 苹果用户：保留原有属性，设置 HiddenInput
#             self.fields['custom_amount'].widget = forms.HiddenInput(
#                 attrs=self.fields['custom_amount'].widget.attrs  # ✅ 保留原有属性
#             )
#             self.fields['custom_amount'].required = False
#         elif platform == 'ANDROID':
#             # 安卓用户：保留原有属性，设置 HiddenInput 和 NumberInput
#             self.fields['recharge_option'].widget = forms.HiddenInput(
#                 attrs=self.fields['recharge_option'].widget.attrs  # ✅ 保留原有属性
#             )
#             self.fields['recharge_option'].required = False
#
#             # 设置 NumberInput 并保留原有属性
#             attrs = self.fields['custom_amount'].widget.attrs.copy()
#             attrs['step'] = '1'
#             self.fields['custom_amount'].widget = forms.NumberInput(attrs=attrs)

class GameOrderAddModelForm(BootStrapForm, forms.ModelForm):
    class Meta:
        model = GameOrder
        fields = ['platform', 'game', 'recharge_option', 'recharge_link', 'qr_code', 'consumer']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['recharge_link'].required = False
        self.fields['qr_code'].required = False
        # 初始化时设置空的recharge_option queryset
        self.fields['recharge_option'].queryset = GameDenomination.objects.none()

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
        elif self.instance.pk:
            self.fields['recharge_option'].queryset = self.instance.game.order_options.filter(
                platform=self.instance.platform
            )


def gameorder_add(request):
    if request.method == 'GET':
        form = GameOrderAddModelForm()
        return render(request, 'gameorder_add.html', {'form': form})

    form = GameOrderAddModelForm(data=request.POST,files=request.FILES)

    if not form.is_valid():
        print('1')
        return render(request, 'gameorder_add.html', {'form': form})

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
            qr_code_path,full_path = get_upload_path(qr_code_file,username)

            # 保存文件
            with open(full_path, 'wb+') as destination:
                for chunk in qr_code_file.chunks():
                    destination.write(chunk)

            # 解析二维码
            qr_link = qr_code_to_link(full_path)
            if not qr_link:
                form.add_error('consumer', '无法解析二维码内容')
                print('2')
                return render(request, 'gameorder_add.html', {'form': form})

            # 更新表单数据
            form.instance.recharge_link = qr_link
            form.instance.qr_code = qr_code_path

        except Exception as e:
            form.add_error('consumer', f'文件处理出错: {str(e)}')
            print(e)
            return render(request, 'gameorder_add.html', {'form': form})

    # 保存订单
    order = form.save(commit=False)
    order.created_by = request.userinfo  # 或 request.userinfo
    order.save()

    messages.success(request, '订单创建成功')
    return redirect('gameorder_list')


from django.http import JsonResponse


# def gameorder_load_charge_options(request):
#     game_id = request.GET.get('game')
#     platform = request.GET.get('platform')
#
#     if not game_id or not platform:
#         return JsonResponse({'status': False, 'error': '缺少参数'})
#
#     options = GameDenomination.objects.filter(
#         game_id=game_id,
#         platform=platform,
#         active=True
#     ).order_by('amount').values('id', 'amount', 'base_currency', 'gift_currency' ,'bonus_currency')
#
#     # 构造包含完整显示文本的选项列表
#     option_list = []
#     for option in options:
#         option_list.append({
#             'id': option.id,
#             'amount': str(option.amount),
#             'base_currency': option.base_currency,
#             'gift_currency': option.gift_currency,
#             'bonus_currency': option.bonus_currency,
#             'total_currency': option.base_currency + option.gift_currency + option.bonus_currency,
#             'display_text': str(option)  # 这会调用__str__方法，即display_text属性
#         })
#
#     return JsonResponse({
#         'status': True,
#         'options': option_list
#     })

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



def gameorder_edit(request,pk):
    pass


def gameorder_delete(request):
    pass