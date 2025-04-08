from django.db.models import Count, Sum, Q, F
from django.db.models.functions import TruncDate, ExtractMonth
from django.http import JsonResponse
from django.shortcuts import render, redirect
from utils.time_filter import filter_by_date_range
from web.models import TransactionRecord, UserInfo, GameOrder


def dashboard_list(request):
    """数据看板主页面"""
    queryset = TransactionRecord.objects.all()

    queryset, start_date, end_date, date_field = filter_by_date_range(request,queryset)

    context = {
        'start_date': start_date.strftime('%Y-%m-%d') if hasattr(start_date, 'strftime') else start_date,
        'end_date': end_date.strftime('%Y-%m-%d') if hasattr(end_date, 'strftime') else end_date,
        'date_field': request.GET.get('date_field', 'created_time'),
    }
    print('123',start_date,end_date)
    return render(request, 'dashboard_list.html',context)


from django.utils import timezone
def chart_bar(request):
    """交易流水柱状图数据"""

    try:
        # 获取当前管理员
        current_admin = request.userinfo.get_root_admin()
        if not current_admin:
            return JsonResponse({"status": False, "error": "管理员不存在"})


        # 基础查询 - 交易记录
        transaction_queryset = TransactionRecord.objects.filter(
            Q(from_user=current_admin) | Q(to_user=current_admin),
            active=1,
            # created_time__date__range=(start_date, end_date)  # 关键过滤条件
        ).exclude(created_time__isnull=True)

        # 基础查询 - 出库订单
        order_queryset = GameOrder.objects.filter(
            created_by=current_admin,
            active=1,
            order_status=2,  # 已支付的订单
            # created_time__date__range=(start_date, end_date)  # 关键过滤条件
        ).exclude(created_time__isnull=True)

        # 调用封装好的函数进行日期过滤
        transaction_queryset, start_date, end_date, date_field = filter_by_date_range(request, transaction_queryset)
        order_queryset, _, _, _ = filter_by_date_range(request, order_queryset)
        print('date_field',date_field)

        # 按天分组统计交易记录
        transaction_data = transaction_queryset.annotate(
            date=TruncDate(date_field)
        ).values('date').annotate(
            # 1. 系统费总和（本圈出库订单的系统费）
            system_fee_total=Sum('system_fee', filter=Q(from_user=current_admin)),
            # 2. 三方借调费总和（圈内被第三方借调的订单的借调费）
            cross_fee_total=Sum('cross_fee', filter=Q(from_user=current_admin, is_cross_circle=True)),
            # 3. 利润总和（本圈出库订单的利润 = 订单金额 - 系统费 - 借调费 - 供应商结算）
            profit_total=Sum(
                F('amount') - F('system_fee') - F('cross_fee') - F('supplier_payment'),
                filter=Q(from_user=current_admin)
            ),
            # 4. 订单总数（包括圈内订单被第三方借调出库和出库圈内订单及出库圈外订单的总和）
            order_count=Count('order', distinct=True)
        ).order_by('date')

        # 按天分组统计出库订单金额
        order_data = order_queryset.annotate(
            date=TruncDate('created_time')
        ).values('date').annotate(
            order_amount=Sum('recharge_option__amount')
        ).order_by('date')

        # 合并日期，确保所有日期都出现在x轴
        all_dates = set()
        all_dates.update(item['date'] for item in transaction_data)
        all_dates.update(item['date'] for item in order_data)
        sorted_dates = sorted(all_dates)

        # 构建按日期索引的数据字典
        data_dict = {}
        for date in sorted_dates:
            data_dict[date] = {
                'system_fee': 0,
                'cross_fee': 0,
                'profit': 0,
                'order_count': 0,
                'order_amount': 0
            }

        # 填充交易数据
        for item in transaction_data:
            date = item['date']
            data_dict[date]['system_fee'] = float(item['system_fee_total'] or 0)
            data_dict[date]['cross_fee'] = float(item['cross_fee_total'] or 0)
            data_dict[date]['profit'] = float(item['profit_total'] or 0)
            data_dict[date]['order_count'] = int(item['order_count'] or 0)

        # 填充订单数据
        for item in order_data:
            date = item['date']
            data_dict[date]['order_amount'] = float(item['order_amount'] or 0)

        # 准备结果数据
        result = {
            "status": True,
            "data": {
                "x_axis": [date.strftime('%m-%d') for date in sorted_dates],
                "series": [
                    {
                        "name": "每日订单数",
                        "type": "bar",
                        "data": [data_dict[date]['order_count'] for date in sorted_dates],
                        "itemStyle": {"color": "#67C23A"}
                    },
                    {
                        "name": "系统费",
                        "type": "bar",
                        "data": [data_dict[date]['system_fee'] for date in sorted_dates],
                        "itemStyle": {"color": "#F56C6C"}
                    },
                    {
                        "name": "三方借调费",
                        "type": "bar",
                        "data": [data_dict[date]['cross_fee'] for date in sorted_dates],
                        "itemStyle": {"color": "#E6A23C"}
                    },
                    {
                        "name": "利润",
                        "type": "bar",
                        "data": [data_dict[date]['profit'] for date in sorted_dates],
                        "itemStyle": {"color": "#409EFF"},
                        "symbol": "circle",
                        "symbolSize": 8,
                        "lineStyle": {
                            "width": 3
                        }
                    },
                    {
                        "name": "出库订单金额",
                        "type": "bar",
                        "data": [data_dict[date]['order_amount'] for date in sorted_dates],
                        "itemStyle": {"color": "#909399"}
                    }
                ]
            }
        }
        return JsonResponse(result)

    except Exception as e:
        return JsonResponse({"status": False, "error": str(e)})

def chart_pie_cross(request):
    """跨圈借调饼图数据"""
    try:
        current_admin = request.userinfo.get_root_admin()
        if not current_admin:
            return JsonResponse({"status": False, "error": "管理员不存在"})

        # 获取筛选参数
        date_field = request.GET.get('date_field', 'created_time')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        # 查询跨圈借调数据
        qs = TransactionRecord.objects.filter(
            charge_type='cross_circle_fee',
            is_cross_circle=True,
            from_user=current_admin,
            active=1
        )

        # 应用日期过滤
        if start_date and end_date:
            date_filter = {
                f"{date_field}__date__gte": start_date,
                f"{date_field}__date__lte": end_date
            }
            qs = qs.filter(**date_filter)

        data = qs.values('to_user__username').annotate(
            order_count=Count('order'),
            total_fee=Sum('cross_fee'),
            total_amount=Sum('amount'),
            final_amount=Sum('amount') - Sum('cross_fee')
        )

        series_data = [{
            'value': float(item['final_amount']),
            'name': item['to_user__username'],
            'order_count': item['order_count'],
            'fee': float(item['total_fee']),
            'total': float(item['total_amount'])
        } for item in data]

        return JsonResponse({
            "status": True,
            "data": series_data
        })

    except Exception as e:
        return JsonResponse({"status": False, "error": str(e)})

# 其他视图函数保持不变...