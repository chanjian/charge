import itertools
import pandas as pd

# 定义充值档位及赠送点券（QB: 赠送点券）
recharge_plans = {
    45: 38,
    68: 55,
    118: 95,
    198: 180,
    348: 315,
    648: 588,
    898: 826,
    1298: 1246
}

# 生成所有可能的组合（最多6次叠加，总金额≤5000QB）
all_combinations = []
for r in range(1, 7):  # 组合次数：1到6次
    for combo in itertools.combinations_with_replacement(recharge_plans.keys(), r):
        total_qb = sum(combo)
        if total_qb <= 5000:
            # 计算总点券
            total_points = total_qb * 10 + sum(recharge_plans[item] for item in combo)
            # 生成计算过程字符串（去掉最外面的中括号）
            calculation = "+".join([f"({qb*10}+{recharge_plans[qb]})" for qb in combo])
            all_combinations.append((total_qb, combo, total_points, calculation))

# 去重并排序
df = pd.DataFrame(all_combinations, columns=["QB数量", "组合", "合计点券", "计算过程"])
df = df.drop_duplicates().sort_values(by="QB数量")

# 导出到Excel（调整列顺序）
df.to_excel("充值组合.xlsx", index=False, columns=["QB数量", "组合", "合计点券", "计算过程"])

# 控制台输出（前5000条，调整顺序）
print("组合格式: (QB数量, 组合, 合计点券, 计算过程)")
for idx, row in df.head(5000).iterrows():
    qb = row["QB数量"]
    combo = row["组合"]
    points = row["合计点券"]
    calculation = row["计算过程"]
    # 格式化组合为元组字符串，例如 (45, 68)
    combo_str = "(" + ", ".join(map(str, combo)) + ")"
    print(f"{idx+1} | QB数量: {qb} | 组合: {combo_str} | 合计点券: {points} | 计算过程: {calculation}")

print("\n数据已成功导出到 充值组合.xlsx")