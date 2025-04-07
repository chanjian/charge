import pandas as pd
import plotly.express as px

# 1. 构造示例数据（添加订单数字段）
data = {
    '出库人': ['管理员A', '客服A', '供应商A', '供应商A', '供应商A'],
    '所属圈子': ['圈子B', '圈子B', '圈子B', '圈子A', '圈子C'],
    '订单数': [1, 1, 1, 2, 1],
    '应付资金': [150, 100, 500, 300, 200],
    '系统费汇总': [15, 10, 50, 30, 20]
}
df = pd.DataFrame(data)

# 2. 生成交互式堆叠柱状图
fig = px.bar(
    df,
    x='出库人',
    y='应付资金',
    color='所属圈子',
    hover_data=['订单数', '系统费汇总'],  # 悬停时显示额外字段
    barmode='stack',                  # 堆叠模式
    title='各出库人的应付资金分布（按圈子）',
    labels={'应付资金': '金额', '出库人': '操作人员'},
    height=500
)

# 3. 自定义悬停提示框格式
fig.update_traces(
    hovertemplate="<br>".join([
        "出库人: %{x}",
        "所属圈子: %{fullData.name}",
        "订单数: %{customdata[0]}",
        "应付资金: %{y}元",
        "系统费: %{customdata[1]}元"
    ])
)

# 4. 保存为独立HTML文件（可双击打开）
fig.write_html("出库资金分析.html", include_plotlyjs='cdn')  # 小体积文件