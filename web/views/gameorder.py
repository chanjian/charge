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

    pager = Pagination(request,queryset)


    context = {
        'pager':pager,
        'keyword':keyword,
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