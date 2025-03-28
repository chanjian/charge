from tencentcloud.common import credential
from tencentcloud.sms.v20210111 import sms_client, models
# from django.conf import settings
from 刷票管理系统2_优化短信登录 import settings
#设置 Django 的环境变量
# import os
# import django
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "刷票管理系统2_优化短信登录.settings")
# django.setup()


#这里分别是SecretId和SecretKey
cred = credential.Credential(str(settings.T_SECRET_ID), str(settings.T_SECRET_KEY))
# cred = credential.Credential(settings.T_SECRET_ID, settings.T_SECRET_ID)
client = sms_client.SmsClient(cred, "ap-guangzhou")

req = models.SendSmsRequest()

#这里是应用管理中的应用列表中的某个应用的ID
req.SmsSdkAppId = "1400935775"

req.SignName = "合肥起风网络科技有限公司"
#国内短信中的正文模板管理中的模板
req.TemplateId = "2261350"
#指定模板中的验证码
req.TemplateParamSet = ["226135"]
#指定接收短信的手机
req.PhoneNumberSet = ["+8616605643102"]
# req.PhoneNumberSet = ["+8617397277674"]

resp = client.SendSms(req)
print(resp, type(resp))
print(resp.SendStatusSet, type(resp.SendStatusSet))
from tencentcloud.sms.v20210111.models import SendSmsResponse
# {"SendStatusSet": [{"SerialNo": "2640:262727967816586500757778766", "PhoneNumber": "+8618630087660", "Fee": 1, "SessionContext": "", "Code": "Ok", "Message": "send success", "IsoCode": "CN"}], "RequestId": "5528d8e4-31c3-41e3-9e6b-ef8006f365cd"}

# [{"SerialNo": "", "PhoneNumber": "+8618630087660", "Fee": 0, "SessionContext": "", "Code": "LimitExceeded.PhoneNumberThirtySecondLimit", "Message": "the number of SMS messages sent from a single mobile number within 30 seconds exceeds the upper limit", "IsoCode": "CN"}] <class 'list'>
# [{"SerialNo": "2640:133731727416586503152335508", "PhoneNumber": "+8615131255089", "Fee": 1, "SessionContext": "", "Code": "Ok", "Message": "send success", "IsoCode": "CN"}]
