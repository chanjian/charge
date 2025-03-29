import os
from utils.pager import Pagination
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect ,HttpResponse
from django.db import transaction
from utils.link import filter_reverse
from utils.media_path import get_upload_path
from utils.pager import Pagination
from utils.qr_code_to_link import qr_code_to_link
from utils.response import BaseResponse
from utils.time_filter import filter_by_date_range
from web import models
from utils.bootstrap import BootStrapForm,BootStrapModelForm
from utils.encrypt import md5
from django.contrib import messages
from django.contrib import messages
from django.contrib.messages.api import get_messages
from web.models import GameOrder,GameDenomination,TransactionRecord
from decimal import Decimal
from itertools import combinations
import logging
logger = logging.getLogger('web')

def gameorder_list(request):
    messages = get_messages(request)
    for msg in messages:
        print(msg)

    keyword = request.GET.get('keyword', '').strip()

    usertype = request.userdict.usertype
    if usertype == 'CUSTOMER':
        queryset = models.GameOrder.objects.filter(consumer=request.userinfo,active=1).all()
    else:
        from django.db.models import F, Case, When, Value, IntegerField
        queryset = models.GameOrder.objects.filter(active=1).annotate(
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
            max_combine = request.GET.get('max_combine', '3')

            try:
                max_combine = int(max_combine)
                if max_combine < 1 or max_combine > 5:  # 限制最大组合数范围
                    max_combine = 3
            except ValueError:
                max_combine = 3

            # 获取有效订单（折扣>75折）
            valid_orders = queryset.filter(
                recharge_option__isnull=False,
                consumer__level__percent__gt=75
            ).select_related('recharge_option', 'consumer__level')

            # 构建amount_discounts字典，记录每个QB档位的最高折扣
            amount_discounts = {}
            for o in valid_orders:
                if o.recharge_option and hasattr(o.consumer, 'level'):
                    amt = o.recharge_option.amount
                    current_discount = o.consumer.level.percent / 100
                    if amt not in amount_discounts or current_discount > amount_discounts[amt]:
                        amount_discounts[amt] = current_discount

            # 查找最佳组合
            qb_results = find_qb_combinations(
                target_qb=qb_target,
                amount_discounts=amount_discounts,
                client_discount=qb_discount,
                max_combine=max_combine
            )

            # 为每个结果添加订单ID信息（实际应用中可能需要）
            for result in qb_results:
                result['order_ids'] = [
                                          o.id for o in valid_orders
                                          if o.recharge_option.amount in result['combination']
                                      ][:len(result['combination'])]

        except (ValueError, TypeError, AttributeError) as e:
            print(f"QB匹配错误: {e}")
            # 可以添加错误消息返回给用户
            # messages.add_message(request, 25, f"QB匹配出错: {str(e)}")

    context = {
        'pager':pager,
        'keyword':keyword,
        'qb_target': qb_target,  # 当前QB目标值
        'qb_discount': request.GET.get('qb_discount', '75'),  # 当前折扣设置
        'max_combine': request.GET.get('max_combine', '3'),  # 当前组合数设置
        'qb_results': qb_results,  # QB匹配结果
        'start_date': start_date,  # 日期筛选相关
        'end_date': end_date,
        'date_field': request.GET.get('date_field', ''),  # 保留日期字段参数
    }
    return render(request, 'gameorder_list.html', context)
    # return render(request, 'gameorder_list.html', locals())


from itertools import combinations_with_replacement

def find_qb_combinations(target_qb, amount_discounts, client_discount, max_combine=3):
    # 确保所有数值都是 Decimal
    target_qb = Decimal(str(target_qb))
    client_discount = Decimal(str(client_discount))

    # 转换 amount_discounts 中的值为 Decimal
    converted_amounts = {}
    for amt, discount in amount_discounts.items():
        converted_amounts[Decimal(str(amt))] = Decimal(str(discount))
    amounts = sorted(amount_discounts.keys())
    results = []

    # 精确匹配检查
    exact_match = next((a for a in amounts if a == target_qb), None)
    if exact_match:
        return [build_combination([exact_match], [amount_discounts[exact_match]], client_discount, target_qb)]

    best_left = None
    best_right = None

    for r in range(1, max_combine + 1):
        for combo in combinations_with_replacement(amounts, r):
            total = sum(combo)
            discounts = [amount_discounts[amt] for amt in combo]

            # 左边界处理
            if total <= target_qb:
                if (not best_left or
                    (target_qb - total) < (target_qb - best_left['total_qb'])):
                    best_left = build_combination(combo, discounts, client_discount, target_qb)

            # 右边界处理
            if total >= target_qb:
                if (not best_right or
                    (total - target_qb) < (best_right['total_qb'] - target_qb)):
                    best_right = build_combination(combo, discounts, client_discount, target_qb)

    if best_left:
        results.append(best_left)
    if best_right and best_right != best_left:
        results.append(best_right)

    return results

from decimal import Decimal, getcontext
def build_combination(combo, discounts, client_discount, target_qb):
    getcontext().prec = 8  # 设置精度
    # 确保所有输入都是 Decimal
    combo = [Decimal(str(x)) for x in combo]
    discounts = [Decimal(str(x)) for x in discounts]
    client_discount = Decimal(str(client_discount))
    target_qb = Decimal(str(target_qb))

    total_qb = sum(combo)
    remaining = target_qb - total_qb

    orders = []
    income = Decimal('0')
    for amt, discount in zip(combo, discounts):
        amt = Decimal(str(amt))
        final_price = amt * discount
        orders.append({
            'amount': amt,
            'discount_percent': int(discount * 100),
            'final_price': final_price
        })
        income += final_price

    service_fee = len(combo) * Decimal('1')
    transfer_fee = len(combo) * Decimal('0.5')
    cost = total_qb * client_discount
    profit = income - cost - service_fee - transfer_fee

    # 生成智能文案
    combo_str = " + ".join(f"{amt}QB" for amt in combo)
    if remaining > 0:
        remaining_text = f"剩余{remaining}QB"
    elif remaining < 0:
        remaining_text = f"需要补{-remaining}QB"
    else:
        remaining_text = "完全匹配"

    # 生成基础订单描述
    order_desc = "+".join(f"{amt}" for amt in combo)

    # 根据剩余QB情况生成不同文案
    if remaining > 0:
        description = (
            f"客户您好，为您安排订单如下{order_desc}={total_qb}*{client_discount:.2f}={cost:.2f}元，"
            f"剩余{remaining:.0f}QB暂无订单匹配。如果您仍然需要处理，请您耐心等待，"
            f"我们将在后续有合适订单时，仍然按照当前折扣为您处理此订单。"
        )
    elif remaining < 0:
        description = (
            f"客户您好，为您安排订单如下{order_desc}={total_qb}*{client_discount:.2f}={cost:.2f}元，"
            f"需要您补冲{abs(remaining):.0f}QB以配合完全处理。"
        )
    else:
        description = (
            f"客户您好，已为您完美匹配订单如下{order_desc}={total_qb}*{client_discount:.2f}={cost:.2f}元，"
            f"数量完全吻合，感谢您的支持！"
        )

    return {
        'combination': combo,
        'total_qb': total_qb,
        'remaining': remaining,  # 注意这里改为有符号数，正数表示剩余，负数表示需要补
        'orders': orders,
        'income': income,  # 新增收入总和
        'cost': cost,
        'service_fee': service_fee,
        'transfer_fee': transfer_fee,
        'profit': profit,
        'description': description
    }


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