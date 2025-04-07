# views.py
from django.utils import timezone
from django.db.models import Count, Sum, Q
from django.shortcuts import render

from web.models import TransactionRecord,GameOrder


def dashboard_list(request):
    # 获取当前用户和管理员
    current_user = request.userinfo
    current_admin = current_user.get_root_admin()
    today = timezone.now().date()

    # 1. 今日已完成订单统计 (order_status=2 表示已完成)
    today_orders = GameOrder.objects.filter(
        order_status=2,
        finished_time__date=today
    ).select_related('created_by', 'consumer', 'consumer__parent')

    # 2. 按创建人(入库人)分组统计
    creator_stats = today_orders.values('created_by__username').annotate(
        total=Count('id'),
        internal=Count('id', filter=Q(consumer__parent=current_admin)),
        external=Count('id', filter=~Q(consumer__parent=current_admin))
    )

    # 3. 跨圈订单统计 - 通过消费者parent判断
    cross_orders = today_orders.exclude(consumer__parent=current_admin)
    cross_admin_stats = cross_orders.values('consumer__parent__username').annotate(
        order_count=Count('id')
    )

    # 4. 从交易记录中获取费用数据
    transactions = TransactionRecord.objects.filter(
        created_time__date=today,
        creator=current_admin
    )

    # 客服数据统计
    support_stats = transactions.filter(
        charge_type__in=['commission', 'advance_pay']
    ).values('to_user__username').annotate(
        commission=Sum('commission'),
        advance=Sum('support_payment')
    )

    # 供应商统计
    supplier_stats = transactions.filter(
        charge_type='supplier_pay'
    ).values('to_user__username').annotate(
        total_payment=Sum('supplier_payment')
    )

    # 费用汇总
    fee_summary = {
        'total_system_fee': transactions.filter(
            charge_type='system_fee'
        ).aggregate(total=Sum('system_fee'))['total'] or 0,
        'total_cross_fee': transactions.filter(
            charge_type='cross_circle_fee'
        ).aggregate(total=Sum('cross_fee'))['total'] or 0
    }

    context = {
        'today': today.strftime("%Y-%m-%d"),
        'creator_stats': creator_stats,  # 改名为creator_stats更准确
        'cross_admin_stats': cross_admin_stats,
        'support_stats': support_stats,
        'supplier_stats': supplier_stats,
        'fee_summary': fee_summary,
        'chart_data': {
            'total_orders': today_orders.count(),
            'internal_external': [
                today_orders.filter(consumer__parent=current_admin).count(),
                today_orders.exclude(consumer__parent=current_admin).count()
            ]
        }
    }
    return render(request, 'dashboard_list.html', context)