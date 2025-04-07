import pandas as pd
import matplotlib.pyplot as plt
# 设置中文字体（Windows系统）
plt.rcParams['font.sans-serif'] = ['Microsoft YaHei']  # 微软雅黑
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
# 1. 构造示例数据
data = {
    '出库人': ['管理员A', '客服A', '供应商A', '供应商A', '供应商A'],
    '所属圈子': ['圈子B', '圈子B', '圈子B', '圈子A', '圈子C'],
    '订单数': [1, 1,  1, 2, 1],
    '应付资金': [1550, 100,  500, 300, 200],
    '系统费汇总': [15, 10,  50, 30, 20]
}
df = pd.DataFrame(data)

# 2. 生成透视表
pivot_table = pd.pivot_table(
    df,
    values=['应付资金', '系统费汇总'],
    index=['出库人'],
    columns=['所属圈子'],
    aggfunc='sum',
    fill_value=0
)

# 3. 可视化：堆叠柱状图
plt.figure(figsize=(10, 6))
pivot_table['应付资金'].plot(kind='bar', stacked=True, colormap='viridis')
plt.title('各出库人的应付资金分布（按圈子）')
plt.ylabel('金额')
plt.xlabel('出库人')
plt.xticks(rotation=-30)
plt.legend(title='所属圈子', bbox_to_anchor=(1, 1))
plt.tight_layout()
plt.show()  # 使用标准plt.show()显示图表

# # 4. 可视化：热力图（需安装seaborn）
# try:
#     import seaborn as sns
#     plt.figure(figsize=(8, 4))
#     sns.heatmap(pivot_table['应付资金'], annot=True, fmt='.0f', cmap='YlGnBu')
#     plt.title('应付资金热力图（出库人 vs 圈子）')
#     plt.tight_layout()
#     plt.show()  # 使用标准plt.show()显示图表
# except ImportError:
#     print("提示：请先安装seaborn库（pip install seaborn）以生成热力图。")