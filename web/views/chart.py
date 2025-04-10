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
            'order__created_by',
            'order__outed_by',
            'order__consumer__level'  # ✅ 确保关联level表
        ).annotate(
            date=TruncDate('created_time')
        )

        # 3. 应用日期过滤
        queryset, start_date, end_date, _ = filter_by_date_range(request, queryset)

        # 4. 定义类型安全的计算表达式
        def calculate_raw_amount(qs):
            """计算原始面额总和（不涉及折扣）"""
            return qs.aggregate(
                total=Coalesce(Sum('order__recharge_option__amount'),
                               Value(0, output_field=DecimalField()))
            )['total']

        def calculate_profit(qs, user_type):
            """
            新版利润计算公式：
            利润 = 客户支付金额(final) - 系统费 - 借调费 - 角色特定支出
            """
            base_expr = ExpressionWrapper(
                (F('order__recharge_option__amount') *
                 F('order__consumer__level__percent') / 100) -  # 客户支付金额
                F('system_fee') -
                F('cross_fee'),
                output_field=DecimalField(max_digits=10, decimal_places=2)
            )

            if user_type == 'SUPPORT':
                base_expr = ExpressionWrapper(
                    base_expr - F('support_payment') - F('commission'),  # ✅ 客服需扣除垫付资金和佣金
                    output_field=DecimalField()
                )
            elif user_type == 'SUPPLIER':
                base_expr = ExpressionWrapper(
                    base_expr - F('supplier_payment'),  # ✅ 供应商需扣除结算款
                    output_field=DecimalField()
                )
            elif user_type == 'ADMIN':
                base_expr = ExpressionWrapper(
                    base_expr - F('admin_payment'),  # ✅ 管理员可能有垫付
                    output_field=DecimalField()
                )

            return qs.filter(
                order__outed_by__usertype=user_type  # ✅ 改为按出库人类型过滤
            ).annotate(
                calc_profit=base_expr
            ).aggregate(
                total=Coalesce(Sum('calc_profit'), Value(0, output_field=DecimalField()))
            )['total']

        # 5. 基础统计（全部使用明确类型）
        date_groups = queryset.values('date').annotate(
            total_raw_amount=Coalesce(
                Sum('order__recharge_option__amount'),
                Value(0, output_field=DecimalField())
            ),
            total_orders=Count('order', distinct=True),
            admin_orders=Count('order',
                               filter=Q(order__outed_by__usertype__in=['ADMIN', 'SUPERADMIN']),
                               distinct=True),
            support_orders=Count('order',
                                 filter=Q(order__outed_by__usertype='SUPPORT'),
                                 distinct=True),
            supplier_orders=Count('order',
                                  filter=Q(order__outed_by__usertype='SUPPLIER'),
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
            ), Value(0, output_field=DecimalField())),

            # ✅ 新增三个垫付资金统计
            support_payment=Coalesce(Sum(
                'support_payment',
                filter=Q(order__outed_by__usertype='SUPPORT'),
                output_field=DecimalField()
            ), Value(0, output_field=DecimalField())),

            supplier_payment=Coalesce(Sum(
                'supplier_payment',
                filter=Q(order__outed_by__usertype='SUPPLIER'),
                output_field=DecimalField()
            ), Value(0, output_field=DecimalField())),

            admin_payment=Coalesce(Sum(
                'admin_payment',
                filter=Q(order__outed_by__usertype__in=['ADMIN', 'SUPERADMIN']),
                output_field=DecimalField()
            ), Value(0, output_field=DecimalField())),
        ).order_by('date')

        # 6. 合并数据（全部使用Decimal处理）
        results = []
        for group in date_groups:
            date = group['date']

            # 计算各类型金额
            admin_amount = calculate_raw_amount(
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

                'total_amount': float(group['total_raw_amount']),
                'admin_amount': float(admin_amount),
                'system_fee': float(group['system_fee']),
                'cross_fee': float(group['cross_fee']),
                'commission': float(group['commission']),

                'support_payment': float(group['support_payment']),  # ✅ 新增
                'supplier_payment': float(group['supplier_payment']),  # ✅ 新增
                'admin_payment': float(group['admin_payment']),  # ✅ 新增

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
                    {"name": "总出库订单数", "type": "bar", "data": [item['total_orders'] for item in results]},
                    {"name": "管理员出库订单", "type": "bar", "data": [item['admin_orders'] for item in results]},
                    {"name": "客服出库订单", "type": "bar", "data": [item['support_orders'] for item in results]},
                    {"name": "供应商出库订单", "type": "bar", "data": [item['supplier_orders'] for item in results]},

                    {"name": "总流水", "type": "bar", "data": [item['total_amount'] for item in results]},
                    {"name": "系统费", "type": "bar", "data": [item['system_fee'] for item in results]},
                    {"name": "三方借调费", "type": "bar", "data": [item['cross_fee'] for item in results]},
                    {"name": "客服佣金", "type": "bar", "data": [item['commission'] for item in results]},

                    # ✅ 新增三个垫付资金折线图
                    {"name": "客服垫付资金","type": "bar","data": [item['support_payment'] for item in results],
                        "symbol": "roundRect",
                        "color": "#FFA500"
                    },
                    {"name": "供应商结算","type": "bar","data": [item['supplier_payment'] for item in results],
                        "symbol": "diamond",
                        "color": "#32CD32"
                    },
                    {"name": "管理员垫付","type": "bar","data": [item['admin_payment'] for item in results],
                        "symbol": "triangle",
                        "color": "#9370DB"
                    },

                    {"name": "总利润", "type": "bar", "data": [item['total_profit'] for item in results]},
                    {"name": "管理员创造的利润", "type": "bar", "data": [item['admin_profit'] for item in results]},
                    {"name": "客服创造的利润", "type": "bar", "data": [item['support_profit'] for item in results]},
                    {"name": "供应商创造的利润", "type": "bar", "data": [item['supplier_profit'] for item in results]}
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