import datetime
import random
from django.core.exceptions import ValidationError
from django.db import models
from decimal import Decimal
from django.db.models import (
    Count, Sum, Q, F, Case, When, Value,
    IntegerField, DecimalField
)

class ActiveBaseModel(models.Model):
    active = models.SmallIntegerField(verbose_name="状态", default=1, choices=((1, "激活"), (0, "删除"),))
    created_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True,null=True,blank=True)
    updated_time = models.DateTimeField(verbose_name="更新时间", auto_now=True)
    finished_time = models.DateTimeField(verbose_name="结束时间",blank=True,null=True)

    class Meta:
        abstract = True

class PricePolicy(ActiveBaseModel):
    """ 价格策略（原价，后续可以根据用级别不同做不同折扣）
    1  1000 80
    2  2000 81
    """
    count = models.IntegerField(verbose_name="数量")
    discount = models.DecimalField(verbose_name="折扣", default=0, max_digits=10, decimal_places=2)
    # 添加创建者字段
    creator = models.ForeignKey(to='UserInfo', verbose_name="创建者", on_delete=models.CASCADE, null=True, blank=True,
                                related_name='created_pricepolicy')


class Level(ActiveBaseModel):
    """ 用户等级表 """
    LEVEL_TYPE_CHOICES = (
        ('CUSTOMER', '消费者等级'),
        ('SUPPLIER', '供应商等级'),
        ('SUPPORT', '客服等级'),
    )

    level_type = models.CharField(verbose_name="等级类型", max_length=16,choices=LEVEL_TYPE_CHOICES, db_index=True, default='CUSTOMER')
    title = models.CharField(verbose_name="等级名称", max_length=32)
    percent = models.IntegerField(verbose_name="折扣百分比", help_text="0-100整数，如90表示90折")
    # 添加创建者字段
    creator = models.ForeignKey(to='UserInfo',verbose_name="创建者",on_delete=models.CASCADE,null=True,blank=True,related_name='created_levels')

    class Meta:
        verbose_name = "用户等级"
        verbose_name_plural = verbose_name
        # 移除全局唯一约束，改为creator+title+level_type的组合唯一
        unique_together = [('creator', 'title', 'level_type')]

    def clean(self):
        """验证同一管理员不能创建重复等级"""
        if not self.creator:  # 如果没有creator（如超级管理员创建）
            return

        if Level.objects.filter(
                creator=self.creator,
                title=self.title,
                level_type=self.level_type,
                active=1
        ).exclude(pk=self.pk).exists():
            raise ValidationError("您已创建过同名同类型的等级！")

    def __str__(self):
          return f"{self.get_level_type_display()}-{self.title}"



class UserInfo(ActiveBaseModel):
    usertype_choice = (
        ('SUPERADMIN', '超级管理员'),
        ('ADMIN', '普通管理员'),
        ('CUSTOMER', '消费者'),
        ('SUPPLIER', '供应商'),
        ('SUPPORT', '客服'),
    )
    username = models.CharField(verbose_name="姓名", max_length=16)
    usertype = models.CharField(verbose_name='用户类型', choices=usertype_choice, default='CUSTOMER',max_length=32)
    password = models.CharField(verbose_name="密码", max_length=64)
    mobile = models.CharField(verbose_name='手机号码', max_length=11, unique=True, null=True, blank=True)
    account = models.DecimalField(verbose_name="账户余额", max_digits=10, decimal_places=2, default=0)  # 消费者/供应商的余额
    # create_time = models.DateTimeField(verbose_name="账户创建时间", auto_now_add=True, null=True, blank=True)
    # 'self'：表示外键指向的是同一个模型（即 UserInfo 模型）。
    # null=True：允许字段为空，表示某些用户（如超级管理员）可能没有创建者。
    # on_delete=models.SET_NULL：如果被引用的用户被删除，则将 parent 字段设置为 NULL，而不是级联删除。
    parent = models.ForeignKey(verbose_name='父级', to='self', null=True, on_delete=models.SET_NULL,related_name='children')
    level = models.ForeignKey(verbose_name='等级',to='Level',null=True,blank=True,related_name='userinfo',on_delete=models.SET_NULL,default=None)

    def __str__(self):
        return self.username

    def get_root_admin(self):
        """获取当前用户的顶级管理员（递归查找父级）"""
        if self.usertype in ['SUPERADMIN', 'ADMIN'] and not self.parent:
            return self
        if self.parent:
            return self.parent.get_root_admin()
        return None  # 如果没有管理员则返回None

class LoginLog(models.Model):
    """登录日志"""
    login_time = models.DateTimeField(verbose_name="登录时间", auto_now_add=True)
    login_ip = models.CharField(verbose_name="登录ip", max_length=18)
    login_city = models.CharField(verbose_name="登录城市", max_length=64, null=True, blank=True)
    login_province = models.CharField(verbose_name="登录省份", max_length=64, null=True, blank=True)
    login_device_type = models.CharField(verbose_name="设备类型", max_length=64, null=True, blank=True)
    login_os = models.CharField(verbose_name="操作系统", max_length=64, null=True, blank=True)
    login_browser = models.CharField(verbose_name="浏览器名称", max_length=64, null=True, blank=True)
    map_location = models.CharField(verbose_name="地图定位", max_length=256, null=True, blank=True)
    exact_address = models.CharField(verbose_name="精确地址", max_length=256, null=True, blank=True)
    user = models.ForeignKey(to=UserInfo, verbose_name="用户", on_delete=models.CASCADE, related_name='loginlog')

class GameName(ActiveBaseModel):
    name = models.CharField(max_length=50, verbose_name='游戏名称')
    # icon = models.ImageField(upload_to='game_icons/', blank=True, null=True, verbose_name='游戏图标')

    class Meta:
        verbose_name = '游戏'
        verbose_name_plural = '游戏'

    def __str__(self):
        return self.name


class GameDenomination(ActiveBaseModel):
    platform = models.CharField(
        max_length=10,
        choices=[
            ('IOS', '苹果'),
            ('ANDROID', '安卓'),
        ],
        verbose_name='充值系统'
    )
    amount = models.DecimalField(max_digits=6, decimal_places=2, verbose_name='充值金额')
    base_currency = models.PositiveIntegerField(verbose_name='基础点券')
    gift_currency = models.PositiveIntegerField(verbose_name='赠送点券',default=0,help_text='用户获得的额外赠送点券')
    bonus_currency = models.PositiveIntegerField(verbose_name='绑定点券',default=0)
    monthly_limit = models.PositiveIntegerField(default=5, verbose_name='每月限购次数')
    game = models.ForeignKey(GameName, on_delete=models.CASCADE, verbose_name='所属游戏',default=None,null=True,related_name='denominations')

    class Meta:
        verbose_name = '充值面额'
        verbose_name_plural = '充值面额'
        ordering = ['platform', 'amount']

    def __str__(self):
        return self.display_text

    @property
    def total_currency(self):
        return self.base_currency + self.gift_currency + self.bonus_currency

    @property
    def display_text(self):
        return f"{self.amount}元档位(总{self.total_currency}点券: {self.base_currency}基础+{self.gift_currency}赠送+{self.bonus_currency}绑定)"


class GameOrder(ActiveBaseModel):
    PLATFORM_CHOICES = [
        ('IOS', '苹果'),
        ('ANDROID', '安卓'),
    ]
    QV_CHOICES = [
        ('Q', 'Q区'),
        ('V', 'V区'),
    ]

    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES, verbose_name='充值系统', default='ANDROID')
    QV = models.CharField(max_length=10,choices=QV_CHOICES,verbose_name='Q区还是V区',default='')
    recharge_option = models.ForeignKey(to=GameDenomination, on_delete=models.PROTECT, null=True, blank=True,verbose_name='充值选项')
    recharge_link = models.URLField(verbose_name='充值链接',max_length=500, blank=True, null=True)
    qr_code = models.ImageField(upload_to='qrcodes/', verbose_name='充值二维码', blank=True, null=True)
    consumer = models.ForeignKey(to=UserInfo, on_delete=models.PROTECT, related_name='consumer_orders',verbose_name='订单消费者')
    created_by = models.ForeignKey(to=UserInfo, on_delete=models.PROTECT, related_name='created_orders',verbose_name='订单入库人')
    outed_by = models.ForeignKey(to=UserInfo, on_delete=models.PROTECT, related_name='outed_orders',verbose_name='订单出库人',default=None,null=True,blank=True)
    order_number = models.CharField(max_length=20, unique=True, verbose_name='订单号')
    order_status_choice = (
        (1, '待支付'),
        (2, '已支付'),
        (3, '超时'),
        (4, '撤单'),
    )
    order_status = models.SmallIntegerField(verbose_name='订单状态', choices=order_status_choice, default=1)  # 新增
    game = models.ForeignKey(GameName, on_delete=models.PROTECT, verbose_name='游戏名称',default=None,null=True)

    class Meta:
        verbose_name = '充值订单'
        verbose_name_plural = '充值订单'

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = self.generate_order_number()
        super().save(*args, **kwargs)

    def generate_order_number(self):
        from datetime import datetime
        return f"O{datetime.now().strftime('%Y%m%d%H%M%S')}"

    @property
    def price_info(self):
        """返回包含所有价格相关信息的字典"""
        # 充值面额一比一的价格
        original = Decimal(str(self.recharge_option.amount)) if self.recharge_option else Decimal('0')
        # 给消费者的折扣
        discount = Decimal(str(self.consumer.level.percent))# / Decimal('100') if hasattr(self.consumer,'level') else Decimal('1')
        # 消费者最终支付价格
        final = original * discount / Decimal('100') if hasattr(self.consumer,'level') else Decimal('1')
        # 最终充值点券到账数目
        points = self.recharge_option.total_currency if self.recharge_option else 0
        composite = round((final * 10) / points, 2) if points > 0 else 0.0

        return {
            'original': original,
            'discount_percent': discount,
            'final': final,
            'received_points': points,
            'composite_discount': composite
        }

    @property
    def description_text(self):
        """动态生成说明文案（基于price_info的数据）"""
        info = self.price_info
        parts = [
            f"本次充值系统为{self.get_platform_display()}",
            f"档位为{self.recharge_option.amount if self.recharge_option else '无'}",
            f"折扣为{info['discount_percent']}%",
            f"实际付款金额应为{info['final']:.2f}元",
            f"实际到账点券为{info['received_points']}",
            f"综合折扣为{info['composite_discount']:.2f}，即{info['composite_discount']*100:.0f}%"
        ]
        return "，".join(parts)


class OrderEditLog(models.Model):
    """订单修改记录（只读）"""
    ACTION_TYPES = (
        ('create', '创建'),
        ('update', '更新'),
        ('delete', '删除'),
    )

    order = models.ForeignKey('GameOrder', on_delete=models.CASCADE, related_name='edit_logs')
    operator = models.ForeignKey('UserInfo', on_delete=models.CASCADE, verbose_name='操作人')
    action = models.CharField('操作类型', max_length=10, choices=ACTION_TYPES)
    changed_fields = models.JSONField('变更字段', default=dict)
    operation_time = models.DateTimeField('操作时间', auto_now_add=True)
    ip_address = models.GenericIPAddressField('IP地址', null=True, blank=True)

    class Meta:
        ordering = ['-operation_time']
        verbose_name = '订单修改记录'
        verbose_name_plural = '订单修改记录'

    def __str__(self):
        return f"{self.order.order_number}-{self.get_action_display()}-{self.operator.username}"


class TransactionRecord(ActiveBaseModel):
    """ 交易记录 """
    charge_type_class_mapping = {
        'recharge': "success",  # 充值 -> 绿色
        'deduction': "danger",  # 扣款 -> 红色
        'system_fee': "default",  # 系统费用 -> 默认
        'cross_circle_fee': "info",  # 跨圈借调费 -> 蓝色
        'commission': "primary",  # 提成费用 -> 深蓝
        'order_create': "warning",  # 创建订单 -> 黄色
        'order_cancel': "secondary",  # 取消订单 -> 灰色
    }
    TRANSACTION_TYPE_CHOICES = (
        # 账户操作类
        ('recharge', '充值'),
        ('deduction', '扣款'),

        # # 订单交易类
        # ('system_fee', '系统费用'),
        # ('cross_circle_fee', '跨圈借调费'),
        # ('commission', '提成费用'),
        # ('advance_pay', '垫付款项'),
        # ('supplier_pay', '供应商结算'),

        # 订单状态类
        ('order_create', '创建订单'),
        ('order_cancel', '取消订单'),
        ('order_complete', '完成订单'),

    )

    charge_type = models.CharField(verbose_name="类型", choices=TRANSACTION_TYPE_CHOICES,max_length=32)
    amount = models.DecimalField(verbose_name="金额", default=0, max_digits=10, decimal_places=2)
    t_id = models.CharField(verbose_name="交易编号", max_length=64, null=True, blank=True, db_index=True)
    customer = models.ForeignKey(verbose_name="客户", to="UserInfo",related_name='customer_userinfo', on_delete=models.CASCADE, null=True, blank=True)
    creator = models.ForeignKey(verbose_name="管理员", to="UserInfo", related_name='creator_userinfo',on_delete=models.CASCADE, null=True, blank=True)
    memo = models.TextField(verbose_name="备注", null=True, blank=True)

    # 关联信息（可选）
    is_cross_circle = models.BooleanField(default=False, verbose_name="是否跨圈")
    order = models.ForeignKey(GameOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')


    # 入库人所属圈子的管理员
    from_user = models.ForeignKey(verbose_name="入库人圈子管理员",to="UserInfo", on_delete=models.PROTECT, related_name='in_transactions', null=True,blank=True)
    # 出库人所属圈子的管理员
    to_user = models.ForeignKey(verbose_name="出库人圈子管理员",to="UserInfo", on_delete=models.PROTECT, related_name='out_transactions', null=True,blank=True)

    # 费用明细（新增核心字段）
    system_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="系统费用")
    cross_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="跨圈费用")
    commission = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="客服提成金额")

    admin_payment = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="管理员付款")
    support_payment = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="客服垫付款")
    supplier_payment = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="供应商结算")

    class Meta:
        indexes = [
            models.Index(fields=['from_user', 'charge_type']),
            models.Index(fields=['is_cross_circle', 'created_time']),
        ]

    def generate_tid(self):
        """生成T+年月日时分秒+3位随机数的交易号"""
        now = datetime.datetime.now()
        # 格式: T + 年月日时分秒 + 3位随机数 (示例: T20240403092548123)
        time_part = now.strftime("%Y%m%d%H%M%S")
        random_part = str(random.randint(100, 999))  # 3位随机数
        return f"T{time_part}{random_part}"