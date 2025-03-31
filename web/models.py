from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import Q  # 确保这行存在
from django.db.models import F
from decimal import Decimal

class ActiveBaseModel(models.Model):
    active = models.SmallIntegerField(verbose_name="状态", default=1, choices=((1, "激活"), (0, "删除"),))
    created_time = models.DateTimeField(verbose_name="创建时间", auto_now_add=True,null=True,blank=True)
    updated_time = models.DateTimeField(verbose_name="更新时间", auto_now=True)
    finished_time = models.DateTimeField(verbose_name="结束时间",blank=True,null=True)

    class Meta:
        abstract = True



class Level(ActiveBaseModel):
    """ 用户等级表 """
    LEVEL_TYPE_CHOICES = (
        ('CUSTOMER', '消费者等级'),
        ('SUPPLIER', '供应商等级'),
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

    platform = models.CharField(max_length=10, choices=PLATFORM_CHOICES, verbose_name='充值系统', default='ANDROID')
    recharge_option = models.ForeignKey(to=GameDenomination, on_delete=models.PROTECT, null=True, blank=True,verbose_name='充值选项')
    recharge_link = models.URLField(verbose_name='充值链接', blank=True, null=True)
    qr_code = models.ImageField(upload_to='qrcodes/', verbose_name='充值二维码', blank=True, null=True)
    consumer = models.ForeignKey(to=UserInfo, on_delete=models.PROTECT, related_name='consumer_orders',verbose_name='订单消费者')
    created_by = models.ForeignKey(to=UserInfo, on_delete=models.PROTECT, related_name='created_orders',verbose_name='订单入库人')
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
        original = Decimal(str(self.recharge_option.amount)) if self.recharge_option else Decimal('0')
        discount = Decimal(str(self.consumer.level.percent)) / Decimal('100') if hasattr(self.consumer,
                                                                                         'level') else Decimal('1')
        final = original * discount
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




class TransactionRecord(ActiveBaseModel):
    """ 交易记录 """
    charge_type_class_mapping = {
        1: "success",
        2: "danger",
        3: "default",
        4: "info",
        5: "primary",
    }
    charge_type_choices = ((1, "充值"), (2, "扣款"), (3, "创建订单"), (4, "删除订单"), (5, "撤单"),)
    charge_type = models.SmallIntegerField(verbose_name="类型", choices=charge_type_choices)
    amount = models.DecimalField(verbose_name="金额", default=0, max_digits=10, decimal_places=2)
    order_oid = models.CharField(verbose_name="订单号", max_length=64, null=True, blank=True, db_index=True)
    create_datetime = models.DateTimeField(verbose_name="交易时间", auto_now_add=True)
    memo = models.TextField(verbose_name="备注", null=True, blank=True)

    customer = models.ForeignKey(verbose_name="客户", to="UserInfo", related_name='customer_transactions',on_delete=models.CASCADE, null=True,blank=True)
    creator = models.ForeignKey(verbose_name="管理员", to="UserInfo", related_name='created_transactions',on_delete=models.CASCADE, null=True,blank=True)
