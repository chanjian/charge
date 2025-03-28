from django.shortcuts import render, redirect,HttpResponse
from utils.response import BaseResponse
from web import models
from django.http import JsonResponse
from django.conf import settings
from web.forms.account import LoginForm,SmsLoginForm,MobileForm

from utils.info.device_detector import DeviceDetector
from utils.info.geoip_providers import GeoIPService
import logging
logger = logging.getLogger('web')


def login(request):
    if request.method == "GET":
        form = LoginForm()
        return render(request, "login.html", {'form': form})

    # 1. 接收并获取数据（数据格式或是否为空验证 - Form 组件 & ModelForm 组件）
    form = LoginForm(data=request.POST)
    if not form.is_valid():
        return render(request, "login.html", {'form': form})

    data_dict = form.cleaned_data

    user_object = models.UserInfo.objects.filter(active=1).filter(**data_dict).first()

    # 2.1 校验失败
    if not user_object:
        return render(request, "login.html", {'form': form, 'error': "用户名或密码错误"})

    # 2.2 校验成功，用户信息写入 session + 进入项目后台
    request.session[settings.SESSION_KEY] = {'usertype':user_object.usertype,'username': user_object.username, 'id': user_object.id}

    # 3. 获取客户端信息并保存到 LoginLog
    # try:
    #     # 获取客户端 IP 地址
    #     ip = GeoIPService.get_client_ip(request)
    #     print(f"IP: {ip}")  # 调试
    #
    #     # 获取地理位置信息
    #     geo_data = GeoIPService.get_location(request)  # 传递 request 对象
    #     print(f"Geo Data: {geo_data}")  # 调试
    #     if 'error' not in geo_data:
    #         # 从多个服务商数据中融合城市信息
    #         login_city = geo_data.get('city', '未知')
    #         login_province = geo_data.get('region', '未知')
    #         map_location = geo_data.get('baidu_map_url', '未知')
    #         exact_address = geo_data.get('exact_address', '未知')
    #     else:
    #         login_city = '未知'
    #         login_province = '未知'
    #         map_location = '未知'
    #         exact_address = '未知'
    #
    #     # 获取设备信息
    #     device_info = DeviceDetector.get_advanced_device_info(request)
    #     print(f"Device Info: {device_info}")  # 调试
    #     login_device_type = device_info['device']['type']  # 使用设备类型
    #     login_os = device_info['os']['family']
    #     login_browser = device_info['browser']['family']
    #
    #     # 创建 LoginLog 记录
    #     login_log = models.LoginLog.objects.create(
    #         login_ip=ip,
    #         login_city=login_city,
    #         login_province=login_province,
    #         login_device_type=login_device_type,
    #         login_os=login_os,
    #         login_browser=login_browser,
    #         map_location=map_location,
    #         exact_address=exact_address,
    #
    #     )
    #     print(f"Login Log Created: {login_log.id}")  # 调试
    #
    # except Exception as e:
    #     logger.error("Failed to save login log: %s", str(e), exc_info=True)
    #     print(f"Error: {e}")  # 调试

    return redirect("/home/")


def sms_login(request):

    if request.method == 'GET':
        form = SmsLoginForm()
        return render(request, "sms_login.html",{'form':form})

    res = BaseResponse()
    print(request.POST)
    #1.手机格式校验
    form = SmsLoginForm(data=request.POST)
    if not form.is_valid():
        res.detail = form.errors
        return JsonResponse(res.dict,json_dumps_params={"ensure_ascii":False})

    #2.短信验证码 + redis中的验证码 =》校验  #写在form的钩子方法中
    mobile = form.cleaned_data['mobile']

    user_object = models.UserInfo.objects.filter(active=1).filter(mobile=mobile).first()

    if not user_object:
        res.detail = {"mobile":["手机号不存在"]}
        return JsonResponse(res.dict)

    # 4. 校验成功，用户信息写入session+进入项目后台
    mapping = {"1": "ADMIN", "2": "CUSTOMER"}
    request.session[settings.NB_SESSION_KEY] = {'name': user_object.username, 'id': user_object.id}
    res.status = True
    res.data = settings.LOGIN_HOME
    return JsonResponse(res.dict)





def sms_send(request):
    # print(request.META.get('X_CSRFTOKEN'))
    # print(request.META.get('HTTP_X_CSRFTOKEN'))
    # print(request.META.get('HTTP_XXX'))
    print('sharon')
    res = BaseResponse()
    #1.校验数据合法性： 手机号的格式 + 角色
    print(request.GET)
    print(request.POST)
    request.POST.get('mobile')
    form = MobileForm(data=request.POST)
    if not form.is_valid():
        print(form.errors.as_data())
        res.detail = form.errors
        return JsonResponse(res.dict, json_dumps_params={'ensure_ascii': False})
        # return JsonResponse({'status': False, 'detail': form.errors}, json_dumps_params={'ensure_ascii': False})
    # #1-1 校验手机号在数据库中是否存在，如果不存在，不允许发送
    # mobile = form.cleaned_data['mobile']
    # role = form.cleaned_data['role']
    #
    # if role == "1":
    #     exists = models.Administrator.objects.filter(active=1, mobile=mobile).exists()
    # else:
    #     exists = models.Customer.objects.filter(active=1, mobile=mobile).exists()
    # if not exists:
    #     res.detail = {"mobile":["手机号不存在"]}
    #     return JsonResponse(res.dict,json_dumps_params={"ensure_ascii":False})



    res.status = True
    res.data = settings.LOGIN_HOME
    return JsonResponse(res.dict)


def logout(request):
    """ 注销 """
    request.session.clear()
    return redirect(settings.LOGIN_URL)


def home(request):

    return render(request,'home.html')

def order(request):

    return HttpResponse('order')






