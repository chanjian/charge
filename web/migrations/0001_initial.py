# Generated by Django 5.2 on 2025-04-24 14:51

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='GameName',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('active', models.SmallIntegerField(choices=[(1, '激活'), (0, '删除')], default=1, verbose_name='状态')),
                ('created_time', models.DateTimeField(auto_now_add=True, null=True, verbose_name='创建时间')),
                ('updated_time', models.DateTimeField(auto_now=True, null=True, verbose_name='更新时间')),
                ('finished_time', models.DateTimeField(blank=True, null=True, verbose_name='结束时间')),
                ('name', models.CharField(max_length=50, verbose_name='游戏名称')),
            ],
            options={
                'verbose_name': '游戏',
                'verbose_name_plural': '游戏',
            },
        ),
        migrations.CreateModel(
            name='Level',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('active', models.SmallIntegerField(choices=[(1, '激活'), (0, '删除')], default=1, verbose_name='状态')),
                ('created_time', models.DateTimeField(auto_now_add=True, null=True, verbose_name='创建时间')),
                ('updated_time', models.DateTimeField(auto_now=True, null=True, verbose_name='更新时间')),
                ('finished_time', models.DateTimeField(blank=True, null=True, verbose_name='结束时间')),
                ('level_type', models.CharField(choices=[('CUSTOMER', '消费者等级'), ('SUPPLIER', '供应商等级'), ('SUPPORT', '客服等级')], db_index=True, default='CUSTOMER', max_length=16, verbose_name='等级类型')),
                ('title', models.CharField(max_length=32, verbose_name='等级名称')),
                ('percent', models.IntegerField(help_text='0-100整数，如90表示90折', verbose_name='折扣百分比')),
            ],
            options={
                'verbose_name': '用户等级',
                'verbose_name_plural': '用户等级',
            },
        ),
        migrations.CreateModel(
            name='LoginLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('active', models.SmallIntegerField(choices=[(1, '激活'), (0, '删除')], default=1, verbose_name='状态')),
                ('created_time', models.DateTimeField(auto_now_add=True, null=True, verbose_name='创建时间')),
                ('updated_time', models.DateTimeField(auto_now=True, null=True, verbose_name='更新时间')),
                ('finished_time', models.DateTimeField(blank=True, null=True, verbose_name='结束时间')),
                ('login_time', models.DateTimeField(auto_now_add=True, verbose_name='登录时间')),
                ('login_ip', models.CharField(max_length=18, verbose_name='登录ip')),
                ('login_city', models.CharField(blank=True, max_length=64, null=True, verbose_name='登录城市')),
                ('login_province', models.CharField(blank=True, max_length=64, null=True, verbose_name='登录省份')),
                ('login_device_type', models.CharField(blank=True, max_length=64, null=True, verbose_name='设备类型')),
                ('login_os', models.CharField(blank=True, max_length=64, null=True, verbose_name='操作系统')),
                ('login_browser', models.CharField(blank=True, max_length=64, null=True, verbose_name='浏览器名称')),
                ('map_location', models.CharField(blank=True, max_length=256, null=True, verbose_name='地图定位')),
                ('exact_address', models.CharField(blank=True, max_length=256, null=True, verbose_name='精确地址')),
            ],
            options={
                'verbose_name': '登录日志',
                'ordering': ['-login_time'],
            },
        ),
        migrations.CreateModel(
            name='GameDenomination',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('active', models.SmallIntegerField(choices=[(1, '激活'), (0, '删除')], default=1, verbose_name='状态')),
                ('created_time', models.DateTimeField(auto_now_add=True, null=True, verbose_name='创建时间')),
                ('updated_time', models.DateTimeField(auto_now=True, null=True, verbose_name='更新时间')),
                ('finished_time', models.DateTimeField(blank=True, null=True, verbose_name='结束时间')),
                ('platform', models.CharField(choices=[('IOS', '苹果'), ('ANDROID', '安卓')], max_length=10, verbose_name='充值系统')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=6, verbose_name='充值金额')),
                ('base_currency', models.PositiveIntegerField(verbose_name='基础点券')),
                ('gift_currency', models.PositiveIntegerField(default=0, help_text='用户获得的额外赠送点券', verbose_name='赠送点券')),
                ('bonus_currency', models.PositiveIntegerField(default=0, verbose_name='绑定点券')),
                ('monthly_limit', models.PositiveIntegerField(default=5, verbose_name='每月限购次数')),
                ('game', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='denominations', to='web.gamename', verbose_name='所属游戏')),
            ],
            options={
                'verbose_name': '充值面额',
                'verbose_name_plural': '充值面额',
                'ordering': ['platform', 'amount'],
            },
        ),
        migrations.CreateModel(
            name='GameOrder',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('active', models.SmallIntegerField(choices=[(1, '激活'), (0, '删除')], default=1, verbose_name='状态')),
                ('created_time', models.DateTimeField(auto_now_add=True, null=True, verbose_name='创建时间')),
                ('updated_time', models.DateTimeField(auto_now=True, null=True, verbose_name='更新时间')),
                ('finished_time', models.DateTimeField(blank=True, null=True, verbose_name='结束时间')),
                ('platform', models.CharField(choices=[('IOS', '苹果'), ('ANDROID', '安卓')], default='ANDROID', max_length=10, verbose_name='充值系统')),
                ('QV', models.CharField(choices=[('Q', 'Q区'), ('V', 'V区')], default='', max_length=10, verbose_name='Q区还是V区')),
                ('recharge_link', models.URLField(blank=True, max_length=500, null=True, verbose_name='充值链接')),
                ('qr_code', models.ImageField(blank=True, null=True, upload_to='qrcodes/', verbose_name='充值二维码')),
                ('order_number', models.CharField(max_length=20, unique=True, verbose_name='订单号')),
                ('order_status', models.SmallIntegerField(choices=[(1, '待支付'), (2, '已支付'), (3, '超时'), (4, '删除')], default=1, verbose_name='订单状态')),
                ('game', models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.PROTECT, to='web.gamename', verbose_name='游戏名称')),
                ('recharge_option', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='web.gamedenomination', verbose_name='充值选项')),
            ],
            options={
                'verbose_name': '充值订单',
                'verbose_name_plural': '充值订单',
            },
        ),
        migrations.CreateModel(
            name='IPDetectionResult',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('provider_name', models.CharField(max_length=64, verbose_name='服务商')),
                ('detection_time', models.DateTimeField(auto_now_add=True, verbose_name='检测时间')),
                ('is_valid', models.BooleanField(default=False, verbose_name='是否有效')),
                ('error_message', models.TextField(blank=True, null=True, verbose_name='错误信息')),
                ('raw_data', models.JSONField(default=dict, verbose_name='原始数据')),
                ('country', models.CharField(blank=True, max_length=64, null=True, verbose_name='国家')),
                ('region', models.CharField(blank=True, max_length=64, null=True, verbose_name='地区')),
                ('city', models.CharField(blank=True, max_length=64, null=True, verbose_name='城市')),
                ('latitude', models.FloatField(blank=True, null=True, verbose_name='纬度')),
                ('longitude', models.FloatField(blank=True, null=True, verbose_name='经度')),
                ('isp', models.CharField(blank=True, max_length=128, null=True, verbose_name='ISP')),
                ('map_url', models.CharField(blank=True, max_length=256, null=True, verbose_name='地图链接')),
                ('exact_address', models.CharField(blank=True, max_length=256, null=True, verbose_name='精确地址')),
                ('login_log', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ip_detection_results', to='web.loginlog')),
            ],
            options={
                'verbose_name': 'IP检测结果',
                'ordering': ['detection_time'],
            },
        ),
        migrations.CreateModel(
            name='QbSearch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('qb', models.IntegerField(verbose_name='QB数量')),
                ('combo', models.CharField(max_length=255, verbose_name='组合')),
                ('points', models.IntegerField(verbose_name='合计点券')),
                ('calculation', models.TextField(verbose_name='计算过程')),
            ],
            options={
                'db_table': 'combinations',
                'indexes': [models.Index(fields=['qb'], name='qb_index')],
                'unique_together': {('qb', 'combo')},
            },
        ),
        migrations.CreateModel(
            name='UserInfo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('active', models.SmallIntegerField(choices=[(1, '激活'), (0, '删除')], default=1, verbose_name='状态')),
                ('created_time', models.DateTimeField(auto_now_add=True, null=True, verbose_name='创建时间')),
                ('updated_time', models.DateTimeField(auto_now=True, null=True, verbose_name='更新时间')),
                ('finished_time', models.DateTimeField(blank=True, null=True, verbose_name='结束时间')),
                ('username', models.CharField(max_length=16, verbose_name='姓名')),
                ('usertype', models.CharField(choices=[('SUPERADMIN', '超级管理员'), ('ADMIN', '普通管理员'), ('CUSTOMER', '消费者'), ('SUPPLIER', '供应商'), ('SUPPORT', '客服')], default='CUSTOMER', max_length=32, verbose_name='用户类型')),
                ('password', models.CharField(max_length=64, verbose_name='密码')),
                ('mobile', models.CharField(blank=True, max_length=11, null=True, unique=True, verbose_name='手机号码')),
                ('account', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='账户余额')),
                ('level', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='userinfo', to='web.level', verbose_name='等级')),
                ('parent', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='children', to='web.userinfo', verbose_name='父级')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='PricePolicy',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('active', models.SmallIntegerField(choices=[(1, '激活'), (0, '删除')], default=1, verbose_name='状态')),
                ('created_time', models.DateTimeField(auto_now_add=True, null=True, verbose_name='创建时间')),
                ('updated_time', models.DateTimeField(auto_now=True, null=True, verbose_name='更新时间')),
                ('finished_time', models.DateTimeField(blank=True, null=True, verbose_name='结束时间')),
                ('count', models.IntegerField(verbose_name='数量')),
                ('discount', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='折扣')),
                ('creator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='created_pricepolicy', to='web.userinfo', verbose_name='创建者')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='OrderEditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('create', '创建'), ('update', '更新'), ('delete', '删除')], max_length=10, verbose_name='操作类型')),
                ('changed_fields', models.JSONField(default=dict, verbose_name='变更字段')),
                ('operation_time', models.DateTimeField(auto_now_add=True, verbose_name='操作时间')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='IP地址')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='edit_logs', to='web.gameorder')),
                ('operator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='web.userinfo', verbose_name='操作人')),
            ],
            options={
                'verbose_name': '订单修改记录',
                'verbose_name_plural': '订单修改记录',
                'ordering': ['-operation_time'],
            },
        ),
        migrations.CreateModel(
            name='OperationLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(max_length=255, verbose_name='操作内容')),
                ('timestamp', models.DateTimeField(auto_now_add=True, verbose_name='操作时间')),
                ('related_object_id', models.PositiveIntegerField(blank=True, null=True, verbose_name='关联对象ID')),
                ('related_object_type', models.CharField(blank=True, max_length=50, null=True, verbose_name='关联对象类型')),
                ('is_own_action', models.BooleanField(default=False, verbose_name='是否本人操作')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='operation_logs', to='web.userinfo', verbose_name='操作用户')),
            ],
            options={
                'verbose_name': '操作记录',
                'verbose_name_plural': '操作记录',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddField(
            model_name='loginlog',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='loginlog', to='web.userinfo', verbose_name='用户'),
        ),
        migrations.AddField(
            model_name='level',
            name='creator',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='created_levels', to='web.userinfo', verbose_name='创建者'),
        ),
        migrations.AddField(
            model_name='gameorder',
            name='consumer',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='consumer_orders', to='web.userinfo', verbose_name='订单消费者'),
        ),
        migrations.AddField(
            model_name='gameorder',
            name='created_by',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='created_orders', to='web.userinfo', verbose_name='订单入库人'),
        ),
        migrations.AddField(
            model_name='gameorder',
            name='outed_by',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='outed_orders', to='web.userinfo', verbose_name='订单出库人'),
        ),
        migrations.CreateModel(
            name='CrossCircleFee',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('active', models.SmallIntegerField(choices=[(1, '激活'), (0, '删除')], default=1, verbose_name='状态')),
                ('created_time', models.DateTimeField(auto_now_add=True, null=True, verbose_name='创建时间')),
                ('updated_time', models.DateTimeField(auto_now=True, null=True, verbose_name='更新时间')),
                ('finished_time', models.DateTimeField(blank=True, null=True, verbose_name='结束时间')),
                ('crossfee_amount', models.DecimalField(decimal_places=2, default=0, help_text='基于订单金额和借调规则计算得出', max_digits=10, verbose_name='跨圈借调费金额')),
                ('payment', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='应收账款')),
                ('borrower', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='borrowed_cross_fees', to='web.userinfo', verbose_name='借入方管理员（出库人圈子）')),
                ('lender', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='lent_cross_fees', to='web.userinfo', verbose_name='借出方管理员（入库人圈子）')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='TransactionRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('active', models.SmallIntegerField(choices=[(1, '激活'), (0, '删除')], default=1, verbose_name='状态')),
                ('created_time', models.DateTimeField(auto_now_add=True, null=True, verbose_name='创建时间')),
                ('updated_time', models.DateTimeField(auto_now=True, null=True, verbose_name='更新时间')),
                ('finished_time', models.DateTimeField(blank=True, null=True, verbose_name='结束时间')),
                ('charge_type', models.CharField(choices=[('recharge', '充值'), ('deduction', '扣款'), ('order_create', '创建订单'), ('order_delete', '删除订单'), ('order_complete', '完成订单'), ('order_outtime', '超时订单')], max_length=32, verbose_name='类型')),
                ('amount', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='金额')),
                ('t_id', models.CharField(blank=True, db_index=True, max_length=64, null=True, verbose_name='交易编号')),
                ('memo', models.TextField(blank=True, null=True, verbose_name='备注')),
                ('is_cross_circle', models.BooleanField(default=False, verbose_name='是否跨圈')),
                ('system_fee', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='系统费用')),
                ('cross_fee', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='跨圈费用')),
                ('commission', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='客服提成金额')),
                ('admin_payment', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='管理员付款')),
                ('support_payment', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='客服垫付款')),
                ('supplier_payment', models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name='供应商结算')),
                ('order', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transactions', to='web.gameorder')),
                ('customer', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='customer_userinfo', to='web.userinfo', verbose_name='客户')),
                ('from_admin', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='in_transactions', to='web.userinfo', verbose_name='入库人圈子管理员')),
                ('operator', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='creator_userinfo', to='web.userinfo', verbose_name='操作人员')),
                ('to_admin', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='out_transactions', to='web.userinfo', verbose_name='出库人圈子管理员')),
            ],
            options={
                'indexes': [models.Index(fields=['from_admin', 'charge_type'], name='web_transac_from_ad_2bb3a2_idx'), models.Index(fields=['is_cross_circle', 'created_time'], name='web_transac_is_cros_d3c38c_idx')],
            },
        ),
        migrations.AlterUniqueTogether(
            name='level',
            unique_together={('creator', 'title', 'level_type')},
        ),
    ]
