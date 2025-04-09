from django.db.models.functions import TruncDate, ExtractMonth, Coalesce
from django.shortcuts import render, redirect
from django.db.models import (
    Count, Sum, Q, F, Case, When, Value,
    IntegerField, DecimalField
)
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from utils.time_filter import filter_by_date_range
from web.models import TransactionRecord, GameOrder
from django.db.models import ExpressionWrapper
import logging
logger = logging.getLogger('web')

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


def chart_bar(request):
    """交易流水柱状图数据（类型安全修正版）"""
    try:
        # 1. 获取当前管理员
        current_admin = request.userinfo.get_root_admin()
        if not current_admin:
            return JsonResponse({"status": False, "error": "管理员不存在"}, status=400)



        # 2. 构建基础查询集（确保所有数值表达式有明确类型）
        queryset = TransactionRecord.objects.filter(
            Q(from_user=current_admin) | Q(to_user=current_admin),
            active=1,
            order__isnull=False,
            order__order_status=2
        ).select_related(
            'order',
            'order__recharge_option',
            'order__consumer',
            'order__created_by'
        ).annotate(
            date=TruncDate('created_time')
        )

        # 3. 应用日期过滤
        queryset, start_date, end_date, _ = filter_by_date_range(request, queryset)

        # 4. 定义类型安全的计算表达式
        def calculate_amount(qs):
            return qs.annotate(
                calc_amount=ExpressionWrapper(
                    F('order__recharge_option__amount') *
                    F('order__consumer__level__percent') / Value(100.0),
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                )
            ).aggregate(
                total=Coalesce(Sum('calc_amount'), Value(0, output_field=DecimalField()))
            )['total']

        def calculate_profit(qs, user_type):
            base_expr = ExpressionWrapper(
                F('order__recharge_option__amount') *
                F('order__consumer__level__percent') / Value(100.0) -
                F('order__recharge_option__amount') *
                F('order__created_by__level__percent') / Value(100.0) -
                F('system_fee') -
                F('cross_fee'),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )

            if user_type == 'SUPPORT':
                base_expr = ExpressionWrapper(
                    base_expr - F('commission'),
                    output_field=DecimalField(max_digits=10, decimal_places=2)
                )

            return qs.filter(
                order__created_by__usertype=user_type
            ).annotate(
                calc_profit=base_expr
            ).aggregate(
                total=Coalesce(Sum('calc_profit'), Value(0, output_field=DecimalField()))
            )['total']

        # 5. 基础统计（全部使用明确类型）
        date_groups = queryset.values('date').annotate(
            total_orders=Count('order', distinct=True),
            admin_orders=Count('order',
                               filter=Q(order__created_by__usertype__in=['ADMIN', 'SUPERADMIN']),
                               distinct=True),
            support_orders=Count('order',
                                 filter=Q(order__created_by__usertype='SUPPORT'),
                                 distinct=True),
            supplier_orders=Count('order',
                                  filter=Q(order__created_by__usertype='SUPPLIER'),
                                  distinct=True),

            system_fee=Coalesce(Sum(
                'system_fee',
                output_field=DecimalField(max_digits=10, decimal_places=2)
            ), Value(0, output_field=DecimalField())),

            cross_fee=Coalesce(Sum(
                'cross_fee',
                output_field=DecimalField(max_digits=10, decimal_places=2)
            ), Value(0, output_field=DecimalField())),

            commission=Coalesce(Sum(
                'commission',
                output_field=DecimalField(max_digits=10, decimal_places=2)
            ), Value(0, output_field=DecimalField()))
        ).order_by('date')

        # 6. 合并数据（全部使用Decimal处理）
        results = []
        for group in date_groups:
            date = group['date']

            # 计算各类型金额
            admin_amount = calculate_amount(
                queryset.filter(
                    date=date,
                    order__created_by__usertype__in=['ADMIN', 'SUPERADMIN']
                )
            )

            results.append({
                'date': date.strftime('%m-%d'),
                'total_orders': group['total_orders'],
                'admin_orders': group['admin_orders'],
                'support_orders': group['support_orders'],
                'supplier_orders': group['supplier_orders'],

                'total_amount': float(calculate_amount(queryset.filter(date=date))),
                'admin_amount': float(admin_amount),
                'system_fee': float(group['system_fee']),
                'cross_fee': float(group['cross_fee']),
                'commission': float(group['commission']),

                'total_profit': float(
                    calculate_profit(queryset.filter(date=date), 'ADMIN') +
                    calculate_profit(queryset.filter(date=date), 'SUPPORT') +
                    calculate_profit(queryset.filter(date=date), 'SUPPLIER')
                ),
                'admin_profit': float(calculate_profit(queryset.filter(date=date), 'ADMIN')),
                'support_profit': float(calculate_profit(queryset.filter(date=date), 'SUPPORT')),
                'supplier_profit': float(calculate_profit(queryset.filter(date=date), 'SUPPLIER'))
            })

        # 7. 构建响应
        return JsonResponse({
            "status": True,
            "data": {
                "x_axis": [item['date'] for item in results],
                "series": [
                    {"name": "总订单数", "type": "bar", "data": [item['total_orders'] for item in results]},
                    {"name": "管理员订单", "type": "bar", "data": [item['admin_orders'] for item in results]},
                    {"name": "客服订单", "type": "bar", "data": [item['support_orders'] for item in results]},
                    {"name": "供应商订单", "type": "bar", "data": [item['supplier_orders'] for item in results]},

                    {"name": "总流水", "type": "bar", "data": [item['total_amount'] for item in results]},
                    {"name": "系统费", "type": "bar", "data": [item['system_fee'] for item in results]},
                    {"name": "三方借调费", "type": "bar", "data": [item['cross_fee'] for item in results]},
                    {"name": "客服佣金", "type": "bar", "data": [item['commission'] for item in results]},

                    {"name": "总利润", "type": "bar", "data": [item['total_profit'] for item in results]},
                    {"name": "管理员利润", "type": "bar", "data": [item['admin_profit'] for item in results]},
                    {"name": "客服利润", "type": "bar", "data": [item['support_profit'] for item in results]},
                    {"name": "供应商利润", "type": "bar", "data": [item['supplier_profit'] for item in results]}
                ]
            }
        })

    except Exception as e:
        import traceback
        return JsonResponse({
            "status": False,
            "error": "数据加载失败",
            "detail": str(e),
            "traceback": traceback.format_exc()
        }, status=500)

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