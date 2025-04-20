from io import BytesIO

from django.db.models import Sum
from django.shortcuts import render, redirect,HttpResponse

from utils.code import check_code
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
from web.models import UserInfo, LoginLog, TransactionRecord
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

    # 验证码的校验
    user_input_code = form.cleaned_data.pop('code')
    code = request.session.get('image_code', "")
    if code.upper() != user_input_code.upper():
        form.add_error("code", "验证码错误")
        return render(request, 'login.html', {'form': form})

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

def image_code(request):
    """ 生成图片验证码 """

    # 调用pillow函数，生成图片
    img, code_string = check_code()

    # 写入到自己的session中（以便于后续获取验证码再进行校验）
    request.session['image_code'] = code_string
    # 给Session设置60s超时
    # request.session.set_expiry(60)

    stream = BytesIO()
    img.save(stream, 'png')
    return HttpResponse(stream.getvalue())

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


def profile(request):
    user = request.userinfo  # 修正为userinfo
    context = {
        'user': user,
        'level': user.level,
        'account_balance': user.account,
        'user_type': user.get_usertype_display(),
        'is_admin': user.usertype in ['SUPERADMIN', 'ADMIN'],
    }

    if user.usertype in ['CUSTOMER', 'SUPPLIER', 'SUPPORT']:
        # 这里可以添加获取公告的逻辑，假设公告模型为 Announcement
        # 暂时先不实现，你可以根据实际情况添加
        context['announcement'] = None

    elif user.usertype in ['ADMIN']:
        # 计算系统费欠款
        system_fee_owed = TransactionRecord.objects.filter(charge_type='system_fee', amount__gt=0).aggregate(Sum('amount'))['amount__sum'] or 0
        context['system_fee_owed'] = system_fee_owed

    elif user.usertype in ['SUPERADMIN']:
        # 超级管理员添加写公告的功能
        # 这里可以添加写公告的逻辑，假设公告模型为 Announcement
        # 暂时先不实现，你可以根据实际情况添加
        context['can_write_announcement'] = True

    return render(request, 'profile.html', context)


def crossfee_manage(request):

    user_object = request.userinfo
    # 查询所有入库人是其他管理员的圈子，而出库人，是当前查看的管理员的圈子
    self_out_other_object = models.CrossCircleFee.objects.exclude(lender=user_object).filter(borrower=user_object).all()
    # 查询所有入口人是当前查看人的圈子，出库人，不是当前查看人的圈子
    other_out_self_object = models.CrossCircleFee.objects.filter(lender=user_object).exclude(borrower=user_object).all()

    context = {
        'self_out_other_object':self_out_other_object,
        'other_out_self_object':other_out_self_object,
    }
    return render(request,'crossfee_manage.html',context)


from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone



def crossfee_clear(request):
    try:
        item_id = request.POST.get('id')
        item_type = request.POST.get('type')

        # 根据类型获取对应的记录
        if item_type == 'self_out':
            item = models.CrossCircleFee.objects.get(id=item_id, borrower=request.userinfo)
        else:
            item = models.CrossCircleFee.objects.get(id=item_id, lender=request.userinfo)

        # 创建操作记录
        if item_type == 'self_out':
            log_message = f"管理员 {request.userinfo.username} 清空了应向 {item.lender.username} 收取的费用"
        else:
            log_message = f"管理员 {request.userinfo.username} 清空了应支付给 {item.borrower.username} 的费用"

        models.OperationLog.objects.create(
            user=request.userinfo,
            action=log_message,
            timestamp=timezone.now()
        )

        # 清空金额
        item.payment = 0
        item.fee_amount = 0
        item.save()

        return JsonResponse({'success': True})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


def get_operation_logs(request):
    logs = models.OperationLog.objects.filter(user=request.userinfo).order_by('-timestamp')
    return render(request, 'partials/operation_logs.html', {'logs': logs})