from django.shortcuts import render, redirect,HttpResponse

from utils.info.create_loginlog import LoginInfoService
from utils.response import BaseResponse
from web import models
from django.http import JsonResponse
from django.conf import settings
from web.forms.account import LoginForm,SmsLoginForm,MobileForm
from utils.info.geoip_providers import GeoIPService
from django.shortcuts import render, redirect
from django.conf import settings
# from web.forms import LoginForm
from web.models import UserInfo,LoginLog
from utils.info.geoip_providers import GeoIPService
from web.tasks import process_login_info  # 直接导入任务函数
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

    # 用户认证
    try:
        data_dict = form.cleaned_data
        user_object = UserInfo.objects.filter(active=1).filter(**data_dict).first()

        # 2.1 校验失败
        if not user_object:
            return render(request, "login.html", {'form': form, 'error': "用户名或密码错误"})

        # 2.2 校验成功，用户信息写入 session + 进入项目后台
        request.session[settings.SESSION_KEY] = {'usertype': user_object.usertype, 'username': user_object.username, 'id': user_object.id}

        # 3. 创建登录记录
        login_log = LoginInfoService.create_login_record(request, user_object)

        # 调用异步任务处理登录信息
        process_login_info.delay(login_log.id, request.META.get('HTTP_USER_AGENT', ''))
        logger.info(f"用户 {user_object.username} 登录成功")

        return redirect("/home/")

    except Exception as e:
        logger.error(f"登录处理失败: {str(e)}", exc_info=True)
        return render(request, "login.html", {
            "form": form,
            "error": "系统错误，请稍后再试"
        })


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
    request.session[settings.NB_SESSION_KEY] = {'name': user_object.username, 'id': user_object.id}
    res.status = True
    res.data = settings.LOGIN_HOME

    # 5. 创建登录记录（异步处理设备信息和IP定位）
    print("===== request.META KEYS =====")
    for key in sorted(request.META):
        print(key)
    ip = GeoIPService.get_client_ip(request)
    print('Extracted IP:', ip)  # 此时应该能看出问题
    # try:
    #     LoginInfoService.create_login_record(request, user_object)
    # except Exception as e:
    #     logger.error(f"创建登录记录失败（不影响登录）: {str(e)}", exc_info=True)
    #     # 即使记录失败也不影响用户登录

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






