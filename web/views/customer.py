from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.db import transaction
from utils.link import filter_reverse
from utils.pager import Pagination
from utils.response import BaseResponse
from web import models
from utils.bootstrap import BootStrapForm,BootStrapModelForm
from utils.encrypt import md5
import logging
logger = logging.getLogger('web')

def customer_list(request):
    usertype = request.userdict.usertype
    user_object = models.UserInfo.objects.filter(username=request.userdict.username).first()
    if usertype == 'SUPERADMIN':
        queryset = models.UserInfo.objects.filter().all()
    else:
        queryset = models.UserInfo.objects.filter(parent=user_object)



    keyword = request.GET.get("keyword", "").strip()
    con = Q()
    if keyword:
        con.connector = 'OR'
        con.children.append(('username__contains', keyword))
        con.children.append(('mobile__contains', keyword))
        con.children.append(('level__title__contains', keyword))

    queryset = queryset.filter(con).filter(active=1).select_related('level','parent')
    # queryset = models.UserInfo.objects.filter(con).filter(active=1).select_related('level')
    obj = Pagination(request, queryset)
    context = {
        "queryset": queryset[obj.start:obj.end],
        "pager_string": obj.html(),
        "keyword": keyword
    }

    return render(request, 'customer_list.html', context)



class CustomerModelForm(BootStrapForm,forms.ModelForm):
    exclude_field_list = ['level']

    confirm_password = forms.CharField(
        label='重复密码',
        widget=forms.PasswordInput(render_value=True)
    )

    class Meta:
        model = models.UserInfo
        fields = ['username', 'mobile', 'password', 'confirm_password', 'level','usertype']
        widgets = {
            'password': forms.PasswordInput(render_value=True),
            'level': forms.RadioSelect
        }

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['level'].queryset = models.Level.objects.filter(active=1,creator=request.userinfo)



    def clean_password(self):
        password = self.cleaned_data.get('password')

        return md5(password)

    def clean_confirm_password(self):
        password = self.cleaned_data.get('password')
        confirm_password = md5(self.cleaned_data.get('confirm_password'))

        if password != confirm_password:
            raise ValidationError('密码不一致')
        return confirm_password


def customer_add(request):
    user_object = models.UserInfo.objects.filter(username=request.userdict.username).first()

    if request.method == 'GET':
        form = CustomerModelForm(request)
        return render(request,'form2.html',{'form':form})

    form = CustomerModelForm(request,data=request.POST)
    if not form.is_valid():
        return render(request, 'form2.html', {'form': form})

    form.instance.parent = user_object
    form.save()
    return redirect('/customer/list/')


class CustomerEditModelForm(BootStrapForm, forms.ModelForm):
    class Meta:
        model = models.UserInfo
        fields = ["username", 'mobile', 'level']
        widgets = {
            'password': forms.PasswordInput(render_value=True)
        }

    def __init__(self, request, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 此处可能用到 request
        self.fields['level'].queryset = models.Level.objects.filter(active=1,creator=request.userinfo)


def customer_edit(request, pk):
    instance = models.UserInfo.objects.filter(id=pk, active=1).first()

    if request.method == 'GET':
        form = CustomerEditModelForm(request, instance=instance)
        return render(request, 'form2.html', {'form': form})

    form = CustomerEditModelForm(request, instance=instance, data=request.POST)
    if not form.is_valid():
        return render(request, 'form2.html', {'form': form})
    form.save()

    return redirect(filter_reverse(request,'/customer/list/'))


class CustomerResetModelForm(BootStrapForm, forms.ModelForm):
    confirm_password = forms.CharField(
        label="重复密码",
        widget=forms.PasswordInput(render_value=True)
    )

    class Meta:
        model = models.UserInfo
        fields = ['password', 'confirm_password']
        widgets = {
            'password': forms.PasswordInput(render_value=True),
        }

    def clean_password(self):
        password = self.cleaned_data['password']

        return md5(password)

    def clean_confirm_password(self):
        password = self.cleaned_data.get('password')
        confirm_password = md5(self.cleaned_data.get('confirm_password', ''))

        if password != confirm_password:
            raise ValidationError("密码不一致")
        return confirm_password


def customer_reset(request, pk):
    from django.core.handlers.wsgi import WSGIRequest
    if request.method == "GET":
        form = CustomerResetModelForm()
        return render(request, 'form2.html', {'form': form})
    instance = models.UserInfo.objects.filter(id=pk, active=1).first()
    form = CustomerResetModelForm(data=request.POST, instance=instance)
    if not form.is_valid():
        return render(request, 'form2.html', {'form': form})
    form.save()
    return redirect("/customer/list/")


def customer_delete(request):
    cid = request.GET.get('cid', 0)
    if not cid:
        res = BaseResponse(status=False, detail="请选择要删除的数据")
        return JsonResponse(res.dict)

    exists = models.UserInfo.objects.filter(id=cid, active=1).exists()
    if not exists:
        res = BaseResponse(status=False, detail="要删除的数据不存在")
        return JsonResponse(res.dict)

    models.UserInfo.objects.filter(id=cid, active=1).update(active=0)
    res = BaseResponse(status=True)
    return JsonResponse(res.dict)


class CustomerChargeModelForm(BootStrapForm,forms.ModelForm):
    charge_type = forms.TypedChoiceField(
        label='类型',
        choices=[(1,'充值'),(2,'扣款')],
        coerce=int,
    )

    class Meta:
        model = models.TransactionRecord
        fields = ['charge_type','amount']


from django.utils import timezone
from datetime import timedelta
def customer_charge(request,pk):
    # 获取查询参数
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    days_range = request.GET.get('days_range')
    print('request.GET',request.GET)

    queryset = models.TransactionRecord.objects.filter(UserInfo_id=pk,UserInfo__active=1,active=1).select_related('UserInfo').order_by('-id')
    pager = Pagination(request,queryset)


    # 根据动态范围计算日期区间
    if days_range:
        days_range = int(days_range)
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days_range)
    else:
        # 将字符串日期转换为带时区的 datetime 对象
        if start_date and end_date:
            start_date = timezone.make_aware(
                timezone.datetime.strptime(start_date, '%Y-%m-%d')
            )
            end_date = timezone.make_aware(
                timezone.datetime.strptime(end_date, '%Y-%m-%d')
            )
        else:
            start_date = None
            end_date = None

    # 根据日期筛选数据
    if start_date and end_date:
        queryset = queryset.filter(create_datetime__range=(start_date, end_date))

    pager = Pagination(request,queryset)
    form = CustomerChargeModelForm()
    context = {
        'pager':pager,
        'form':form,
        'pk':pk,
        'start_date': start_date.strftime('%Y-%m-%d') if start_date else '',
        'end_date': end_date.strftime('%Y-%m-%d') if end_date else '',
    }
    # return render(request,'customer_charge.html',context)
    return render(request, 'customer_charge.html', locals())

    # form = CustomerModelForm(data=request.POST)
    # if not form.is_valid():
    #     return render(request, 'customer_charge.html', {'form': form})
    # return




def customer_charge_add(request,pk):
    form = CustomerChargeModelForm(data=request.POST)
    if not form.is_valid():
        return JsonResponse({"status":False,'detail':form.errors})

    amount = form.cleaned_data['amount']
    charge_type = form.cleaned_data['charge_type']
    try:
        with transaction.atomic():
            cus_object = models.UserInfo.objects.filter(id=pk,active=1).select_for_update().first()

            if charge_type == 2 and cus_object.balance < amount:
                return JsonResponse(
                    {'status': False, 'detail': {"amount": ["余额不足，账户总余额只有:{}".format(cus_object.balance)]}})

            if charge_type == 1:
                cus_object.balance = cus_object.balance + amount
            else:
                cus_object.balance = cus_object.balance - amount
            cus_object.save()

            form.instance.UserInfo = cus_object
            form.instance.creator_id = request.userinfo.id
            form.save()
    except Exception as e:
        return JsonResponse({'status': False, 'detail': {"amount": ["操作失败"],},},json_dumps_params={'ensure_ascii': False})

    return JsonResponse({'status':True})


class CustomerLoginLogForm(BootStrapModelForm):

    class Meta:
        model = models.LoginLog
        fields = "__all__"

def customer_login_log(request,pk):

    queryset = models.LoginLog.objects.filter(UserInfo_id=pk,UserInfo__active=1).select_related('UserInfo').order_by('-id')
    pager = Pagination(request, queryset)

    # 调用封装好的函数进行日期过滤
    from utils.time_filter import filter_by_date_range
    queryset, start_date, end_date, pager = filter_by_date_range(request, queryset)

    form = CustomerLoginLogForm()
    return render(request,'customer_login_log.html',locals())

