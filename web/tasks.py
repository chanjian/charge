from celery import shared_task
import logging

logger = logging.getLogger('web')

@shared_task(bind=True, max_retries=3, ignore_result=False)
def process_login_info(self, id, user_agent):
    """
    异步处理登录信息
    :param user_agent: 客户端的 User-Agent 字符串
    :param ip: 客户端的 IP 地址
    """
    try:
        from utils.info.create_loginlog import LoginInfoService
        # Now process the login info
        print('12312312')
        LoginInfoService.process_login_info(id, user_agent)


    except Exception as exc:
        logger.error(f"登录信息处理失败：{str(exc)}", exc_info=True)
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 5)
