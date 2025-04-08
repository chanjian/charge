from django.db.models import Count, Sum, Q
from django.db.models.functions import TruncDate, ExtractMonth
from django.http import JsonResponse
from django.shortcuts import render
from datetime import datetime, timedelta
from web.models import TransactionRecord, UserInfo


def chart_list(request):
    """数据看板主页面"""
    return render(request, 'chart_list.html')


def chart_bar(request):
    """交易流水柱状图数据"""
    try:
        # 获取当前管理员
        current_admin = request.userinfo.get_root_admin()
        if not current_admin:
            return JsonResponse({"status": False, "error": "管理员不存在"})

        # 获取筛选参数
        date_field = request.GET.get('date_field', 'created_time')
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')

        # 验证日期字段
        if date_field not in ['created_time', 'updated_time', 'finished_time']:
            date_field = 'created_time'

        # 设置默认日期范围（最近7天）
        if not start_date or not end_date:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=7)

        # 基础查询
        qs = TransactionRecord.objects.filter(
            Q(from_user=current_admin) | Q(to_user=current_admin),
            active=1
        )

        # 应用日期过滤
        date_filter = {
            f"{date_field}__date__gte": start_date,
            f"{date_field}__date__lte": end_date
        }
        qs = qs.filter(**date_filter)

        # 按天分组统计
        data = qs.annotate(
            date=TruncDate(date_field)
        ).values('date').annotate(
            income=Sum('amount', filter=Q(to_user=current_admin)),
            expense=Sum('amount', filter=Q(from_user=current_admin))
        ).order_by('date')

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