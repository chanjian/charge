import os
import sys
import django

# 设置正确的项目根目录路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

# 必须在导入模型前设置 Django 环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SemiAutomaticChargeSystem.settings')
django.setup()

from web.models import GameOrderOption

# 王者荣耀充值数据 (金额, 赠送点券, 合计点券)
recharge_data = [
    (45, 38, 488),
    (68, 55, 735),
    (118, 95, 1275),
    (198, 180, 2160),
    (348, 315, 3795),
    (648, 588, 7068),
    (898, 826, 9806),
    (1298, 1246, 14226),
    (1998, 5260, 22060),
    (4998, 5206, 55240),
    (9998, 10520, 110500),
]


def insert_data():
    # 先删除现有数据（可选）
    GameOrderOption.objects.all().delete()

    # IOS平台数据
    for amount, bonus, total in recharge_data:
        GameOrderOption.objects.create(
            platform='IOS',
            amount=amount,
            base_currency=total - bonus,
            bonus_currency=bonus,
            monthly_limit=5 if amount <= 648 else 3,
            is_active=True
        )

    # Android平台数据
    for amount, bonus, total in recharge_data:
        GameOrderOption.objects.create(
            platform='ANDROID',
            amount=amount,
            base_currency=total - bonus,
            bonus_currency=bonus,
            monthly_limit=10,
            is_active=True
        )

    print(f"成功插入 {len(recharge_data) * 2} 条充值选项数据")


if __name__ == '__main__':
    insert_data()