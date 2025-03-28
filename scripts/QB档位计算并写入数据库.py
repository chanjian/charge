import itertools
import os
import django
from NB_Platform import settings
# 设置 Django 环境
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "your_project.settings")

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "NB_Platform.settings")
django.setup()

from web.models import QbSearch  # 导入 QbSearch 模型

# 充值档位及赠送点券
RECHARGE_PLANS = {
    45: 38, 68: 55, 118: 95, 198: 180,
    348: 315, 648: 588, 898: 826, 1298: 1246
}
MAX_TIMES = 6  # 最大叠加次数
MAX_QB = 5000  # 最大QB限制

def generate_combinations():
    """生成所有组合并保存到数据库"""
    # 清空旧数据
    QbSearch.objects.all().delete()

    # 生成所有组合
    for times in range(1, MAX_TIMES + 1):
        for combo in itertools.combinations_with_replacement(RECHARGE_PLANS.keys(), times):
            qb_total = sum(combo)
            if qb_total > MAX_QB:
                continue

            # 计算总点券
            total_points = qb_total * 10 + sum(RECHARGE_PLANS[item] for item in combo)

            # 生成计算过程
            calculation = "+".join([f"({qb}*10+{RECHARGE_PLANS[qb]})" for qb in combo])

            # 保存到数据库
            QbSearch.objects.create(
                qb=qb_total,
                combo=",".join(map(str, combo)),
                points=total_points,
                calculation=calculation
            )

    print("组合数据生成完毕！")

if __name__ == "__main__":
    generate_combinations()