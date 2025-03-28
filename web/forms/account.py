import random

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django_redis import get_redis_connection
from django import forms

from utils import tencent
from utils.encrypt import md5
from web import models


class LoginForm(forms.Form):

    username = forms.CharField(
        label='用户名',
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "用户名"})
    )
    password = forms.CharField(
        label='密码',
        required=True,
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "密码"},render_value=True)
    )

    # def clean_username(self):
    #     return

    def clean_password(self):
        return md5(self.cleaned_data['password'])





class SmsLoginForm(forms.Form):
    role = forms.ChoiceField(
        label="角色",
        required=True,
        choices=(("2", "客户"), ("1", "管理员")),
        widget=forms.Select(attrs={"class": "form-control"})
    )

    mobile = forms.CharField(
        label="手机号",
        validators=[RegexValidator(r'^1[3658]\d{9}$', '手机格式错误'), ],
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "手机号"})
    )

    code = forms.CharField(
        label="短信验证码",
        validators=[RegexValidator(r'^[0-9]{6}$', '验证码格式错误'), ],
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "短信验证码"})
    )

    # def clean_mobile(self):
    #     role = self.cleaned_data.get('role')
    #     mobile = self.cleaned_data['mobile']
    #     if not role:
    #         return mobile
    #
    #     if role == "1":
    #         user_object = models.Administrator.objects.filter(active=1, mobile=mobile).first()
    #     else:
    #         user_object = models.Customer.objects.filter(active=1, mobile=mobile).first()
    #
    #     if not user_object:
    #         raise ValidationError("手机号不存在-钩子【clean_mobile】")
    #     return mobile

    def clean_code(self):
        mobile = self.cleaned_data.get('mobile')
        code = self.cleaned_data['code']
        if not mobile:
            return code

        conn = get_redis_connection("default")
        cache_code = conn.get(mobile)
        if not cache_code:
            raise ValidationError("短信验证码未发送或失效")

        if code != cache_code.decode('utf-8'):
            raise ValidationError("短信验证码未发送或失效")

        return code




class MobileForm(forms.Form):
    role = forms.ChoiceField(
        label="角色",
        required=True,
        choices=(("2", "客户"), ("1", "管理员")),
        widget=forms.Select(attrs={"class": "form-control"})
    )

    mobile = forms.CharField(
        label="手机号",
        required=True,
        validators=[RegexValidator(r'^1[3568]\d{9}$', '手机格式错误'), ]
    )

    def clean_mobile(self):
        role = self.cleaned_data.get('role')
        mobile = self.cleaned_data['mobile']
        if not role:
            return mobile

        if role == "1":
            exists = models.Administrator.objects.filter(active=1, mobile=mobile).exists()
        else:
            exists = models.Customer.objects.filter(active=1, mobile=mobile).exists()
        if not exists:
            raise ValidationError("手机号不存在-钩子【clean_mobile】")

        # 2.发送短信 + 生成验证码
        sms_code = str(random.randint(100000, 999999))
        is_success = tencent.send_sms(mobile, sms_code)
        if not is_success:
            # res.detail = {"mobile": "发送短信失败，请稍后重试"}
            # return JsonResponse(res.dict, json_dumps_params={'ensure_ascii': False})
            raise ValidationError("短信发送失败-钩子【clean_mobile】")

        # 3.将手机号和验证码保存（以便于下次校验） redis -> 超时时间
        conn = get_redis_connection("default")
        conn.set(mobile, sms_code, ex=60)

        return mobile

