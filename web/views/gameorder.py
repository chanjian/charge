from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect ,HttpResponse
from django.db import transaction
from utils.link import filter_reverse
from utils.pager import Pagination
from utils.response import BaseResponse
from web import models
from utils.bootstrap import BootStrapForm,BootStrapModelForm
from utils.encrypt import md5
from django.contrib import messages
from django.contrib.messages.api import get_messages
from web.models import GameOrder,GameDenomination,TransactionRecord
import logging
logger = logging.getLogger('web')

def gameorder_list(request):
    messages = get_messages(request)
    for msg in messages:
        print(msg)
    usertype = request.userdict.usertype
    if usertype == 'CUSTOMER':
        queryset = models.GameOrder.objects.filter(consumer=request.userinfo,active=1).all()
    else:
        queryset = models.GameOrder.objects.filter(active=1).all()

    context = {
        'queryset':queryset,
    }
    return render(request, 'gameorder_list.html', context)

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
    form = GameOrderAddModelForm(request.POST, request.FILES)
    if  not form.is_valid():
        return render(request, 'gameorder_add.html', {'form': form})
    order = form.save(commit=False)
    order.created_by = request.userinfo
    order.save()
    messages.add_message(request, 25, '订单创建成功')
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