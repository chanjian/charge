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


from django.utils import timezone
from datetime import timedelta
from web.models import GameOrder
from django.db import transaction
from web import models

@shared_task
def check_orders_timeout():
    """检查并标记超过48小时未支付的订单为超时状态，并归还用户余额"""
    timeout_threshold = timezone.now() - timedelta(hours=10)

    # 获取所有超时的订单
    timeout_orders = models.GameOrder.objects.filter(
        order_status=1,  # 待支付状态
        created_time__lte=timeout_threshold  # 建议使用创建时间而非更新时间
    )

    order_numbers = "\n".join([order.order_number for order in timeout_orders])

    with transaction.atomic():
        for order in timeout_orders:
            # 获取对应的消费者对象
            consumer_object = order.consumer
            # 计算已扣除的金额，通过price_info属性获取
            price_info = order.price_info
            real_price = price_info['final']

            # 归还余额
            consumer_object.account += real_price
            consumer_object.save()

            # 将订单状态更新为超时状态
            order.order_status = 3
            order.save()

            # 生成TransactionRecord
            transaction_record = models.TransactionRecord.objects.create(
                charge_type='order_outtime',  # 这表示扣款类型
                amount=real_price,
                customer_id=consumer_object.id,  # 使用消费者的 ID
                order=order,
                # creator=request.userinfo,  # 操作的管理员
                memo="超时订单，系统自动标记"
            )

            # 调用模型中的 generate_tid 方法生成交易编号
            transaction_record.t_id = transaction_record.generate_tid()
            # 保存实例，更新 t_id 字段
            transaction_record.save()

    return f"成功标记 {len(timeout_orders)} 个超时订单，并归还相应余额。\n订单号如下：\n{order_numbers}"