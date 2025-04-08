from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncDate, ExtractMonth
from django.http import JsonResponse
from django.shortcuts import render
from datetime import datetime, timedelta

from utils.time_filter import filter_by_date_range
from web.models import TransactionRecord, UserInfo


def chart_list(request):
    """数据看板主页面"""

    # 获取当前用户
    current_admin = UserInfo.objects.filter(username=request.userinfo.username).first()

    # 设置默认日期范围（今天）
    today = datetime.now().date()
    start_date = request.GET.get('start_date', today.strftime('%Y-%m-%d'))
    end_date = request.GET.get('end_date', today.strftime('%Y-%m-%d'))

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'date_field': request.GET.get('date_field', 'created_time'),
    }
    return render(request, 'dashboard_list.html', context)


def chart_bar(request):
    """交易流水柱状图数据"""
    try:
        # # 获取当前管理员
        # current_admin = request.userinfo.get_root_admin()
        # if not current_admin:
        #     return JsonResponse({"status": False, "error": "管理员不存在"})
        # if request.userinfo.usertype == 'ADMIN':
        current_admin = UserInfo.objects.filter(username=request.userinfo.username).first()

        # 基础查询
        queryset = TransactionRecord.objects.filter(Q(from_user=current_admin) | Q(to_user=current_admin), active=1)

        # 2. 应用日期过滤（使用您的函数）
        queryset, start_date_str, end_date_str, date_field = filter_by_date_range(request, queryset)


        # 按天分组统计
        data = queryset.annotate(date=TruncDate(date_field)).values('date').annotate(
            income=Sum('amount', filter=Q(to_user=current_admin)),
            expense=Sum('amount', filter=Q(from_user=current_admin))
        ).order_by('date')
        # print('data',data)
        # print('queryset',queryset)
        # print('queryset.ordernum',queryset.values('order_number'))

        result = {
            "status": True,
            "data": {
                "x_axis": [item['date'].strftime('%m-%d') for item in data],
                "series": [
                    {
                        "name": "收入",
                        "type": "bar",
                        "data": [float(item['income'] or 0) for item in data],
                        "itemStyle": {"color": "#67C23A"}
                    },
                    {
                        "name": "支出",
                        "type": "bar",
                        "data": [float(item['expense'] or 0) for item in data],
                        "itemStyle": {"color": "#F56C6C"}
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

        # 基础查询
        queryset = TransactionRecord.objects.filter(
            charge_type='cross_circle_fee',
            is_cross_circle=True,
            from_user=current_admin,
            active=1
        )
        # 2. 应用日期过滤（使用您的函数）
        queryset, start_date_str, end_date_str, date_field = filter_by_date_range(request, queryset)


        data = queryset.values('to_user__username').annotate(
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