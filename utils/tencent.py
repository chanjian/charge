from tencentcloud.common import credential
from tencentcloud.sms.v20210111 import sms_client, models
from django.conf import settings


def send_sms(mobile, sms_code):
    mobile = "+86{}".format(mobile)
    try:
        cred = credential.Credential(settings.T_SECRET_ID, settings.T_SECRET_KEY)
        client = sms_client.SmsClient(cred, "ap-guangzhou")

        req = models.SendSmsRequest()

        # 这里是应用管理中的应用列表中的某个应用的ID
        req.SmsSdkAppId = "1400935775"

        req.SignName = "合肥起风网络科技有限公司"
        # 国内短信中的正文模板管理中的模板
        req.TemplateId = "2261350"

        req.TemplateParamSet = [sms_code, ]
        req.PhoneNumberSet = [mobile, ]

        resp = client.SendSms(req)
        print(resp.SendStatusSet)
        data_object = resp.SendStatusSet[0]

        from tencentcloud.sms.v20210111.models import SendStatus
        print(data_object.Code)
        if data_object.Code == "Ok":
            return True
    except Exception as e:
        print(e)
