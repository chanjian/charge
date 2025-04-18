# Generated by Django 3.2 on 2025-04-02 15:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('web', '0013_auto_20250402_2316'),
    ]

    operations = [
        migrations.AlterField(
            model_name='transactionrecord',
            name='charge_type',
            field=models.CharField(choices=[('recharge', '充值'), ('deduction', '扣款'), ('system_fee', '系统费用'), ('cross_circle_fee', '跨圈借调费'), ('commission', '提成费用'), ('advance_pay', '垫付款项'), ('supplier_pay', '供应商结算'), ('order_create', '创建订单'), ('order_cancel', '取消订单')], max_length=32, verbose_name='类型'),
        ),
    ]
