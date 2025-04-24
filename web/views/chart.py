from collections import defaultdict
from django.db.models.functions import TruncDate, ExtractMonth, Coalesce
from django.shortcuts import render, redirect
from django.db.models import (
    Count, Sum, Q, F, Case, When, Value,
    IntegerField, DecimalField
)
from django.utils.timezone import localtime
from utils.time_filter import filter_by_date_range
from web.models import TransactionRecord, GameOrder
from django.db.models import ExpressionWrapper
from django.utils import timezone
from django.db.models import Q, Count, Sum, F, Value
from django.db.models import DecimalField
from django.http import JsonResponse
import logging
logger = logging.getLogger('web')

def dashboard_list(request):
    """数据看板主页面"""
    queryset = TransactionRecord.objects.all()

    # queryset, start_date_str, end_date_str, date_field = filter_by_date_range(request,queryset)
    package = filter_by_date_range(request, queryset)

    # context = {
    #     'start_date': start_date.strftime('%Y-%m-%d') if hasattr(start_date, 'strftime') else start_date,
    #     'end_date': end_date.strftime('%Y-%m-%d') if hasattr(end_date, 'strftime') else end_date,
    #     'date_field': request.GET.get('date_field', 'created_time'),
    # }
    context = {
        **package
        # 'start_str':start_date_str,
        # 'end_str':end_date_str,
        # 'date_field':date_field,
    }
    return render(request, 'dashboard_list.html',context)





def chart_bar(request):
    """交易流水柱状图数据（累计统计版）"""
    try:
        current_admin = request.userinfo.get_root_admin()
        if not current_admin:
            return JsonResponse({"status": False, "error": "管理员不存在"}, status=400)

        # 基础查询集
        queryset = TransactionRecord.objects.filter(
            Q(from_admin=current_admin) | Q(to_admin=current_admin),
            active=1,
            order__isnull=False,
            order__outed_by__usertype__in = ['ADMIN','SUPPORT','SUPPLIER'], #确保出库人类型在这三个之间
            order__order_status=2,
        ).select_related(
            'order', 'order__recharge_option', 'order__consumer',
            'order__created_by', 'order__outed_by', 'order__consumer__level'
        )

        # 应用日期过滤
        date_filter = filter_by_date_range(request, queryset)
        queryset = date_filter['queryset']
        start_date = date_filter['start_date_str']
        end_date = date_filter['end_date_str']

        # 计算累计统计数据
        total_stats = {
            'total_orders': queryset.count(),
            # 本圈管理员出库本圈订单数     条件：出库人类型是管理员 且 出库人所属圈子的管理员名字和当前的登录用户一致
            'admin_orders': queryset.filter(order__outed_by__usertype ='ADMIN').filter(from_admin=current_admin).filter(to_admin=current_admin).count(),
            # 本圈客服出库本圈订单数  条件：出库人类型是客服 且 出库人所属圈子的管理员名字和当前的登录用户一致
            'support_orders': queryset.filter(order__outed_by__usertype='SUPPORT').filter(from_admin=current_admin).filter(to_admin=current_admin).count(),
            # 本圈供应商出库本圈订单数  条件：出库人类型是供应商 且 出库人所属圈子的管理员名字和当前的登录用户一致
            'supplier_orders': queryset.filter(order__outed_by__usertype='SUPPLIER').filter(from_admin=current_admin).filter(to_admin=current_admin).count(),
            # 其他圈出库本圈订单数     条件：出库人所属圈子的管理员名字和当前的登录用户不一致
            'other_out_self_orders': queryset.filter(~Q(to_admin=current_admin)).count(),
            # 本圈出库其他圈订单数     条件：出库人所属圈子的管理员名字和当前的登录用户不一致
            'self_out_other_orders': queryset.filter(~Q(from_admin=current_admin)).filter(Q(to_admin=current_admin)).count(),
            # 本圈应支付系统费   条件： 出库人是本圈的
           'system_fee': queryset.filter(to_admin=current_admin).aggregate(total=Sum('system_fee', output_field=DecimalField()))['total'] or 0,
            # 本圈应支付三方借调费  条件：本圈出库其他圈子订单的合计三方借调费   不包含其他圈子出库本圈的借调费
            'cross_fee': queryset.filter(~Q(from_admin=current_admin)).filter(Q(to_admin=current_admin)).aggregate(total=Sum('cross_fee', output_field=DecimalField()))['total'] or 0,
            # 总流水
           #  'total_amount':queryset.aggregate(total=Sum('order__recharge_option__amount', output_field=DecimalField()))['total'] or 0,
           #  'commission': queryset.aggregate(total=Sum('commission', output_field=DecimalField()))['total'] or 0,
           # 'support_payment': queryset.filter(order__outed_by__usertype='SUPPORT').aggregate(total=Sum('support_payment', output_field=DecimalField()))['total'] or 0,
           # 'supplier_payment': queryset.filter(order__outed_by__usertype='SUPPLIER').aggregate(total=Sum('supplier_payment', output_field=DecimalField()))['total'] or 0,
           #  'admin_payment': queryset.filter(order__outed_by__usertype__in=['ADMIN', 'SUPERADMIN']).aggregate(total=Sum('admin_payment', output_field=DecimalField()))['total'] or 0,
        }

        # 计算利润
        def calculate_profit(qs, user_type):
            """计算指定类型的利润"""
            base_expr = ExpressionWrapper(
                (F('order__recharge_option__amount') *
                 F('order__consumer__level__percent') / 100) -
                F('system_fee') -
                F('cross_fee'),
                output_field=DecimalField()
            )

            if user_type == 'SUPPORT':
                base_expr = ExpressionWrapper(
                    base_expr - F('support_payment') - F('commission'),
                    output_field=DecimalField()
                )
            elif user_type == 'SUPPLIER':
                base_expr = ExpressionWrapper(
                    base_expr - F('supplier_payment'),
                    output_field=DecimalField()
                )
            elif user_type == 'ADMIN':
                base_expr = ExpressionWrapper(
                    base_expr - F('admin_payment'),
                    output_field=DecimalField()
                )

            return qs.filter(
                order__outed_by__usertype=user_type
            ).annotate(
                calc_profit=base_expr
            ).aggregate(
                total=Coalesce(Sum('calc_profit'), Value(0, output_field=DecimalField()))
            )['total'] or 0

        # total_stats['admin_profit'] = calculate_profit(queryset, 'ADMIN')
        # total_stats['support_profit'] = calculate_profit(queryset, 'SUPPORT')
        # total_stats['supplier_profit'] = calculate_profit(queryset, 'SUPPLIER')
        # total_stats['total_profit'] = (total_stats['admin_profit'] +total_stats['support_profit'] +total_stats['supplier_profit'])

        # 准备系列数据
        series = [
            {"name": "总出库订单数", "type": "bar", "data": [float(total_stats['total_orders'])]},
            {"name": "本圈管理员出库本圈订单", "type": "bar", "data": [float(total_stats['admin_orders'])]},
            {"name": "本圈客服出库本圈订单", "type": "bar", "data": [float(total_stats['support_orders'])]},
            {"name": "本圈供应商出库本圈订单", "type": "bar", "data": [float(total_stats['supplier_orders'])]},

            {"name": "圈外出库本圈订单", "type": "bar", "data": [float(total_stats['other_out_self_orders'])]},
            {"name": "本圈出库圈外订单", "type": "bar", "data": [float(total_stats['self_out_other_orders'])]},
            # {"name": "总流水", "type": "bar", "data": [float(total_stats['total_amount'])]},
            {"name": "系统费", "type": "bar", "data": [float(total_stats['system_fee'])]},
            {"name": "三方借调费", "type": "bar", "data": [float(total_stats['cross_fee'])]},
            # {"name": "客服佣金", "type": "bar", "data": [float(total_stats['commission'])]},
            # {"name": "客服垫付资金", "type": "bar", "data": [float(total_stats['support_payment'])],"color": "#FFA500"},
            # {"name": "供应商结算", "type": "bar", "data": [float(total_stats['supplier_payment'])], "color": "#32CD32"},
            # {"name": "管理员垫付", "type": "bar", "data": [float(total_stats['admin_payment'])], "color": "#9370DB"},
            # {"name": "总利润", "type": "bar", "data": [float(total_stats['total_profit'])]},
            # {"name": "管理员创造的利润", "type": "bar", "data": [float(total_stats['admin_profit'])]},
            # {"name": "客服创造的利润", "type": "bar", "data": [float(total_stats['support_profit'])]},
            # {"name": "供应商创造的利润", "type": "bar", "data": [float(total_stats['supplier_profit'])]}
        ]

        # 收集订单详情
        order_details = []
        for record in queryset:
            final_price = (record.order.recharge_option.amount *
                           record.order.consumer.level.percent / 100)
            profit = final_price - record.system_fee - record.cross_fee

            if record.order.outed_by.usertype == 'SUPPORT':
                profit -= (record.support_payment or 0) + (record.commission or 0)
            elif record.order.outed_by.usertype == 'SUPPLIER':
                profit -= (record.supplier_payment or 0)
            elif record.order.outed_by.usertype in ['ADMIN', 'SUPERADMIN']:
                profit -= (record.admin_payment or 0)

            order_details.append({
                'order_number': record.order.order_number,
                'original_amount': float(record.order.recharge_option.amount),
                'final_price': float(final_price),
               'system_fee': float(record.system_fee),
                'cross_fee': float(record.cross_fee),
                'profit': float(profit),
                'consumer': record.order.consumer.username,
                'out_admin': record.order.outed_by.username if record.order.outed_by else '未知',
                'out_admin_type': record.order.outed_by.get_usertype_display() if record.order.outed_by else '未知',
                'time': timezone.localtime(record.created_time).strftime('%Y-%m-%d %H:%M'),
                'order_status': record.order.get_order_status_display()
            })

        return JsonResponse({
            "status": True,
            "data": {
                "date_range": f"{start_date} 至 {end_date}",
                "dates": [f"{start_date} 至 {end_date}"],  # 单一日期间隔
                "series": series,
                "tooltip_data": {"汇总": order_details},  # 所有订单详情
                "total_stats": {k: float(v) for k, v in total_stats.items()}  # 用于tooltip显示
            }
        })

    except Exception as e:
        logger.error(f"交易流水统计错误: {str(e)}", exc_info=True)
        return JsonResponse({
            "status": False,
            "error": "数据加载失败",
            "detail": str(e)
        }, status=500)



def chart_consumer(request):
    """消费者消费统计（统一风格重构）"""
    try:
        current_user = request.userinfo
        if not current_user:
            return JsonResponse({"status": False, "error": "用户不存在"}, status=400)

        # 查询基础数据
        queryset = GameOrder.objects.filter(
            order_status=2,  # 已完成订单
            active=1,
        ).select_related('consumer', 'recharge_option', 'consumer__level')

        # 应用日期过滤
        date_filter = filter_by_date_range(request, queryset)
        queryset = date_filter['queryset']
        start_date = date_filter['start_date_str']
        end_date = date_filter['end_date_str']

        # 根据用户类型添加不同的过滤条件
        if current_user.usertype in ['SUPERADMIN', 'ADMIN']:
            queryset = queryset.filter(consumer__parent=current_user)
        elif current_user.usertype == 'CUSTOMER':
            # 消费者只能看到自己的数据
            queryset = queryset.filter(consumer=current_user)
        else:
            return JsonResponse({"status": False, "error": "无权访问"}, status=403)

        # 统一数据结构
        consumer_data = defaultdict(lambda: {
            'total_consumption': 0,
            'order_count': 0,
            'orders': []
        })

        # 处理数据
        for order in queryset:
            consumer_name = order.consumer.username if order.consumer else "未知消费者"
            percent = order.consumer.level.percent if order.consumer and order.consumer.level else 100
            amount = float(order.recharge_option.amount) if order.recharge_option else 0
            final_price = (amount * percent) / 100

            # 累加统计数据
            consumer_data[consumer_name]['total_consumption'] += final_price
            consumer_data[consumer_name]['order_count'] += 1

            # 存储订单详情
            consumer_data[consumer_name]['orders'].append({
                'order_number': order.order_number,
                'original_amount': amount,
                'final_price': final_price,
                'consumer_level': percent,
                'status': order.get_order_status_display(),
                'created_time': localtime(order.created_time).strftime('%Y-%m-%d %H:%M') if order.created_time else None
            })

        # 准备图表数据
        all_consumers = sorted(consumer_data.keys())
        date_range_label = f"{start_date} 至 {end_date}"

        # 生成颜色映射
        consumer_colors = {
            consumer: f'hsl({i * 360 / len(all_consumers)}, 50%, 65%)'
            for i, consumer in enumerate(all_consumers)
        }

        # 构建系列数据
        series = [{
            'name': consumer,
            'type': 'bar',
            'data': [consumer_data[consumer]['total_consumption']],
            'itemStyle': {'color': consumer_colors[consumer]},
            'emphasis': {'itemStyle': {'shadowBlur': 10}},
            'label': {
                'show': True,
                'position': 'top',
                'formatter': '{c}元'
            }
        } for consumer in all_consumers]

        return JsonResponse({
            "status": True,
            "data": {
                "date_range": date_range_label,
                "dates": [date_range_label],
                "series": series,
                "consumers": all_consumers,
                "tooltip_data": {"汇总": consumer_data},
                "colors": consumer_colors
            }
        })

    except Exception as e:
        logger.error(f"消费者统计错误: {str(e)}", exc_info=True)
        return JsonResponse({
            "status": False,
            "error": "数据加载失败",
            "detail": str(e)
        }, status=500)


def chart_supplier(request):
    """供应商统计（统一时间范围处理）"""
    try:
        current_user = request.userinfo
        if not current_user:
            return JsonResponse({"status": False, "error": "用户不存在"}, status=400)

        # 查询基础数据
        queryset = TransactionRecord.objects.filter(
            active=1,
            order__isnull=False,
            order__order_status=2,
            order__outed_by__usertype='SUPPLIER',

            charge_type='order_complete',
        ).select_related('order', 'order__outed_by', 'order__recharge_option')

        # 根据用户类型添加不同的过滤条件
        if current_user.usertype in ['SUPERADMIN', 'ADMIN']:
            # 管理员只能看到自己创建的供应商的数据
            queryset = queryset.filter(
                order__outed_by__usertype='SUPPLIER',
                order__outed_by__parent=current_user  # 供应商的创建者是当前管理员
            )
        elif current_user.usertype == 'SUPPLIER':
            # 供应商只能看到自己的数据
            queryset = queryset.filter(
                order__outed_by=current_user  # 订单的出库人是当前供应商
            )
        else:
            return JsonResponse({"status": False, "error": "无权访问"}, status=403)

        # 应用日期过滤
        date_filter = filter_by_date_range(request, queryset)
        queryset = date_filter['queryset']
        date_field = date_filter['date_field']
        start_date = date_filter['start_date_str']
        end_date = date_filter['end_date_str']

        # 统一数据结构
        supplier_data = defaultdict(lambda: {
            'total_payment': 0,
            'order_count': 0,
            'orders': []
        })

        # 处理数据 - 简化逻辑，因为查询集已经按权限过滤
        for record in queryset:
            # 现在所有记录都符合权限要求，直接使用outed_by的用户名
            supplier_name = record.order.outed_by.username if record.order and record.order.outed_by else "未知供应商"
            # 累加统计数据
            supplier_data[supplier_name]['total_payment'] += float(record.supplier_payment)
            supplier_data[supplier_name]['order_count'] += 1

            # 存储订单详情
            supplier_data[supplier_name]['orders'].append({
                'order_number': record.order.order_number,
                'amount': float(record.order.recharge_option.amount) if record.order.recharge_option else 0,
                'payment': float(record.supplier_payment),
                'created_time': localtime(record.created_time).strftime(
                    '%Y-%m-%d %H:%M') if record.created_time else None
            })

        # 准备图表数据
        all_suppliers = sorted(supplier_data.keys())
        date_range_label = f"{start_date} 至 {end_date}"

        # 生成颜色映射
        supplier_colors = {
            supplier: f'hsl({i * 360 / len(all_suppliers)}, 50%, 65%)'
            for i, supplier in enumerate(all_suppliers)
        }

        # 构建系列数据
        series = [{
            'name': supplier,
            'type': 'bar',
            'data': [supplier_data[supplier]['total_payment']],
            'itemStyle': {'color': supplier_colors[supplier]},
            'emphasis': {'itemStyle': {'shadowBlur': 10}},
            'label': {
                'show': True,
                'position': 'top',
                'formatter': '{c}元'
            }
        } for supplier in all_suppliers]

        return JsonResponse({
            "status": True,
            "data": {
                "date_range": date_range_label,
                "dates": [date_range_label],
                "series": series,
                "suppliers": all_suppliers,
                "tooltip_data": {"汇总": supplier_data},
                "colors": supplier_colors
            }
        })

    except Exception as e:
        logger.error(f"供应商统计错误: {str(e)}", exc_info=True)
        return JsonResponse({
            "status": False,
            "error": "数据加载失败",
            "detail": str(e)
        }, status=500)



def chart_support(request):
    """客服统计（统一时间范围处理）"""
    try:
        current_user = request.userinfo
        if not current_user:
            return JsonResponse({"status": False, "error": "用户不存在"}, status=400)

        # 查询基础数据
        queryset = TransactionRecord.objects.filter(
            active=1,
            order__isnull=False,
            order__order_status=2,
            order__outed_by__usertype='SUPPORT',
            charge_type='order_complete',
        ).select_related('order', 'order__outed_by', 'order__recharge_option')

        # 根据用户类型添加不同的过滤条件
        if current_user.usertype in ['SUPERADMIN', 'ADMIN']:
            # 管理员只能看到自己创建的供应商的数据
            queryset = queryset.filter(
                order__outed_by__usertype='SUPPORT',
                order__outed_by__parent=current_user  # 供应商的创建者是当前管理员
            )
        elif current_user.usertype == 'SUPPORT':
            # 供应商只能看到自己的数据
            queryset = queryset.filter(
                order__outed_by=current_user  # 订单的出库人是当前供应商
            )
        else:
            return JsonResponse({"status": False, "error": "无权访问"}, status=403)

        # 应用日期过滤
        date_filter = filter_by_date_range(request, queryset)
        queryset = date_filter['queryset']
        date_field = date_filter['date_field']
        start_date = date_filter['start_date_str']
        end_date = date_filter['end_date_str']

        # 统一数据结构
        support_data = defaultdict(lambda: {
            'support_payment': 0,
            'commission': 0,
            'order_count': 0,
            'final_support_payment': 0,
            'orders': []
        })

        # 处理数据
        for record in queryset:
            support_name = record.order.outed_by.username if record.order and record.order.outed_by else "未知客服"

            # 累加统计数据
            support_data[support_name]['support_payment'] += float(record.support_payment)
            support_data[support_name]['commission'] += float(record.commission)
            support_data[support_name]['order_count'] += 1
            support_data[support_name]['final_support_payment'] += float(record.support_payment) + float(record.commission)

            # 存储订单详情
            support_data[support_name]['orders'].append({
                'order_number': record.order.order_number,
                'amount': float(record.order.recharge_option.amount) if record.order.recharge_option else 0,
                'support_payment': float(record.support_payment),
                'final_support_payment': float(record.support_payment) + float(record.commission),
                'commission': float(record.commission),
                'created_time': localtime(record.created_time).strftime(
                    '%Y-%m-%d %H:%M') if record.created_time else None
            })

        # 准备图表数据
        all_supports = sorted(support_data.keys())
        date_range_label = f"{start_date} 至 {end_date}"

        # 生成颜色映射
        support_colors = {
            support: f'hsl({i * 360 / len(all_supports)}, 50%, 65%)'
            for i, support in enumerate(all_supports)
        }

        # 构建系列数据
        series = [{
            'name': support,
            'type': 'bar',
            'data': [support_data[support]['final_support_payment']],
            'itemStyle': {'color': support_colors[support]},
            'emphasis': {'itemStyle': {'shadowBlur': 10}},
            'label': {
                'show': True,
                'position': 'top',
                'formatter': '{c}元'
            }
        } for support in all_supports]

        return JsonResponse({
            "status": True,
            "data": {
                "date_range": date_range_label,
                "dates": [date_range_label],
                "series": series,
                "supports": all_supports,
                "tooltip_data": {"汇总": support_data},
                "colors": support_colors
            }
        })

    except Exception as e:
        logger.error(f"客服统计错误: {str(e)}", exc_info=True)
        return JsonResponse({
            "status": False,
            "error": "数据加载失败",
            "detail": str(e)
        }, status=500)

def chart_self_out_other(request):
    """本圈出库其他圈子订单统计（统一时间范围处理）"""
    try:
        current_admin = request.userinfo.get_root_admin()
        if not current_admin:
            return JsonResponse({"status": False, "error": "管理员不存在"}, status=400)

        # 查询基础数据
        queryset = TransactionRecord.objects.filter(
            Q(to_admin=current_admin) &
            ~Q(from_admin=current_admin) &
            Q(order__outed_by__isnull=False)
        ).select_related(
            'order', 'order__recharge_option',
            'order__outed_by', 'order__consumer__level', 'from_admin'
        )

        # 应用日期过滤
        date_filter = filter_by_date_range(request, queryset)
        queryset = date_filter['queryset']
        date_field = date_filter['date_field']
        start_date = date_filter['start_date_str']  # 格式: YYYY-MM-DD
        end_date = date_filter['end_date_str']     # 格式: YYYY-MM-DD

        # 统一数据结构
        admin_data = defaultdict(lambda: {
            'order_count': 0,
            'original_amount': 0,
            'receivable': 0,
            'cross_fee': 0,
            'final_receivable': 0,
            'orders': []
        })

        # 处理数据
        for record in queryset.exclude(from_admin__isnull=True):
            admin_name = record.from_admin.username
            final_price = (record.order.recharge_option.amount *
                         record.order.consumer.level.percent / 100)

            # 累加统计数据  tooltip的数据汇总
            admin_data[admin_name]['order_count'] += 1
            admin_data[admin_name]['original_amount'] += float(record.order.recharge_option.amount)
            admin_data[admin_name]['receivable'] += float(final_price)
            admin_data[admin_name]['final_receivable'] += float(final_price) - float(record.cross_fee)
            admin_data[admin_name]['cross_fee'] += float(record.cross_fee)

            # 存储订单详情
            admin_data[admin_name]['orders'].append({
                'order_number': record.order.order_number,
                'original_amount': float(record.order.recharge_option.amount),
                'receivable': float(final_price),
                'final_receivable': float(final_price) - float(record.cross_fee),
                'cross_fee': float(record.cross_fee),
                'consumer': record.order.consumer.username,
                'in_admin': record.from_admin.username,
                'out_admin_type': record.order.outed_by.get_usertype_display() if record.order.outed_by else '未知',
                'time': localtime(getattr(record, date_field)).strftime('%Y-%m-%d %H:%M'),
                'order_status': record.order.get_order_status_display()
            })

        # 准备图表数据
        all_admins = sorted(admin_data.keys())
        date_range_label = f"{start_date} 至 {end_date}"

        # 生成颜色映射
        admin_colors = {
            admin: f'hsl({180 + i * 60 % 360}, 40%, 70%)'  # 柔和的蓝绿色系
            for i, admin in enumerate(all_admins)
        }

        # 构建系列数据
        series = [{
            'name': admin,
            'type': 'bar',
            'data': [admin_data[admin]['receivable']],
            'itemStyle': {'color': admin_colors[admin]},
            'emphasis': {'itemStyle': {'shadowBlur': 10}},
            'label': {
                'show': True,
                'position': 'top',
                'formatter': '{c}元'
            }
        } for admin in all_admins]

        return JsonResponse({
            "status": True,
            "data": {
                "date_range": date_range_label,
                "dates": [date_range_label],
                "series": series,
                "admins": all_admins,
                "tooltip_data": {"汇总": admin_data},
                "colors": admin_colors
            }
        })

    except Exception as e:
        logger.error(f"本圈出库统计错误: {str(e)}", exc_info=True)
        return JsonResponse({
            "status": False,
            "error": "数据加载失败",
            "detail": str(e)
        }, status=500)

def chart_other_out_self(request):
    """其他圈子出库本圈订单统计（统一时间范围处理）"""
    try:
        current_admin = request.userinfo.get_root_admin()
        if not current_admin:
            return JsonResponse({"status": False, "error": "管理员不存在"}, status=400)

        # 查询基础数据
        queryset = TransactionRecord.objects.filter(
            Q(from_admin=current_admin) &
            ~Q(to_admin=current_admin) &
            Q(order__outed_by__isnull=False)
        ).select_related(
            'order', 'order__recharge_option',
            'order__outed_by', 'order__consumer__level', 'to_admin'
        )

        # 应用日期过滤
        date_filter = filter_by_date_range(request, queryset)
        queryset = date_filter['queryset']
        date_field = date_filter['date_field']
        start_date = date_filter['start_date_str']  # 格式: YYYY-MM-DD
        end_date = date_filter['end_date_str']     # 格式: YYYY-MM-DD

        # 统一数据结构
        admin_data = defaultdict(lambda: {
            'order_count': 0,
            'original_amount': 0,
            'payment': 0,
            'cross_fee': 0,
            'final_payment': 0,
            'orders': []
        })

        # 处理数据
        for record in queryset:
            admin_name = record.to_admin.username
            final_price = (record.order.recharge_option.amount *
                         record.order.consumer.level.percent / 100)

            # 累加统计数据 这里的数据，用于tooltip的数据展示
            admin_data[admin_name]['order_count'] += 1
            admin_data[admin_name]['original_amount'] += float(record.order.recharge_option.amount)
            admin_data[admin_name]['payment'] += float(final_price)
            admin_data[admin_name]['cross_fee'] += float(record.cross_fee)
            admin_data[admin_name]['final_payment'] += float(final_price) - float(record.cross_fee)

            # 存储订单详情  这里的数据，用于点击柱状图，展开的表格
            admin_data[admin_name]['orders'].append({
                'order_number': record.order.order_number,
                'original_amount': float(record.order.recharge_option.amount),
                'payment': float(final_price),
                'cross_fee': float(record.cross_fee),
                'final_payment': float(final_price) - float(record.cross_fee),

                'consumer': record.order.consumer.username,
                'out_admin': record.to_admin.username,
                'out_admin_type': record.order.outed_by.get_usertype_display() if record.order.outed_by else '未知',
                'time': localtime(getattr(record, date_field)).strftime('%Y-%m-%d %H:%M'),
                'order_status': record.order.get_order_status_display()
            })

        # 准备图表数据
        all_admins = sorted(admin_data.keys())
        date_range_label = f"{start_date} 至 {end_date}"

        # 生成颜色映射
        admin_colors = {
            admin: f'hsl({i * 360 / len(all_admins)}, 65%, 65%)'
            for i, admin in enumerate(all_admins)
        }

        # 构建系列数据
        series = [{
            'name': admin,
            'type': 'bar',
            'data': [admin_data[admin]['final_payment']],
            'itemStyle': {'color': admin_colors[admin]},
            'emphasis': {'itemStyle': {'shadowBlur': 10}},
            'label': {
                'show': True,
                'position': 'top',
                'formatter': '{c}元'
            }
        } for admin in all_admins]

        return JsonResponse({
            "status": True,
            "data": {
                "date_range": date_range_label,  # 新增日期范围字段
                "dates": [date_range_label],     # 保持数组结构，但只有一个元素
                "series": series,
                "admins": all_admins,
                "tooltip_data": {"汇总": admin_data},  # 统一放在"汇总"键下
                "colors": admin_colors
            }
        })

    except Exception as e:
        logger.error(f"其他圈子出库统计错误: {str(e)}", exc_info=True)
        return JsonResponse({
            "status": False,
            "error": "数据加载失败",
            "detail": str(e)
        }, status=500)



# 之前的按照日期来确定x轴的旧模式
# def chart_other_out_self(request):
#     """其他圈子出库本圈订单统计（分组柱状图版）"""
#     try:
#         current_admin = request.userinfo.get_root_admin()
#         if not current_admin:
#             return JsonResponse({"status": False, "error": "管理员不存在"}, status=400)
#
#         # 查询其他圈子出库到本圈的订单
#         # 第一次数据过滤  筛选入库方是本圈且出库方不是本圈的数据
#         queryset = TransactionRecord.objects.filter(
#             Q(from_user=current_admin) &  # 入库方是本圈
#             ~Q(to_user=current_admin) &  # 出库方不是本圈
#             Q(order__outed_by__isnull=False)  # 确保outed_by存在
#         ).select_related(
#             'order',
#             'order__recharge_option',
#             'order__outed_by',
#             'order__consumer__level',
#             'to_user'  # 关键修改：使用to_user作为出库方标识
#         )
#
#         # 应用日期过滤
#         # 第二次数据过滤 根据前端用户设置的日期范围（如果没有设置，则启用默认设置）
#         queryset = filter_by_date_range(request, queryset)['queryset']
#         # 获取用户选择的筛选方式
#         date_field = filter_by_date_range(request, queryset)['date_field']
#         # print('date_field:',date_field)
#
#         # 构建核心数据结构
#         date_admin_data = defaultdict(lambda: defaultdict(lambda: {
#             'order_count': 0,
#             'original_amount': 0,
#             'payment': 0,
#             'cross_fee': 0,
#             'orders': []
#         }))
#
#         for record in queryset:
#             # local_time = localtime(record.created_time)
#             # 将数据库中的UTC时间转化为Django的setings中设置的本地时间，即东八区
#             # local_time = localtime(record.date_field) #这样的方式是错误的，因为它会将date_field视为record的字段名，不会转义为对应的字符串
#             # 使用 getattr 动态获取 record 对象的属性
#             selected_date = getattr(record, date_field)
#             local_time = localtime(getattr(record, date_field))
#             print('selected_date:', selected_date)
#             print('local_time:', local_time)
#
#             date_str = local_time.strftime('%m-%d')
#             print('date_str: ', date_str)
#             admin_name = record.to_user.username  # 关键修改：使用出库方的管理者名称
#
#             # 获取出库人类型
#             out_user_type = record.order.outed_by.get_usertype_display() if record.order.outed_by else '未知'
#
#             # 计算最终价格,即给点券客户的价格
#             final_price = (record.order.recharge_option.amount * record.order.consumer.level.percent / 100)
#
#             # 累加统计数据
#             date_admin_data[date_str][admin_name]['order_count'] += 1
#             date_admin_data[date_str][admin_name]['original_amount'] += float(record.order.recharge_option.amount)
#             date_admin_data[date_str][admin_name]['payment'] += float(final_price)
#             date_admin_data[date_str][admin_name]['cross_fee'] += float(record.cross_fee)
#
#             # 存储订单详情
#             date_admin_data[date_str][admin_name]['orders'].append({
#                 'order_number': record.order.order_number,
#                 'original_amount': float(record.order.recharge_option.amount),
#                 'final_price': float(final_price) + float(record.cross_fee),
#                 'cross_fee': float(record.cross_fee),
#                 'consumer': record.order.consumer.username,
#                 'out_admin': record.to_user.username,
#                 'out_admin_type': out_user_type,
#                 'time': local_time.strftime('%Y-%m-%d %H:%M'),
#                 'order_status': record.order.get_order_status_display()
#             })
#
#             """
#             复杂嵌套字典实例演示
#             {
#                 "05-01": {
#                     "root1": {
#                         "order_count": 1,
#                         "original_amount": 100,
#                         "payment": 95,
#                         "cross_fee": 5,
#                         "orders": [
#                             {
#                                 "order_number": "ORD-001",
#                                 "original_amount": 100,
#                                 "final_price": 95,
#                                 "cross_fee": 5,
#                                 "out_admin": "root1"
#                             }
#                         ]
#                     },
#                     "root2": {
#                         "order_count": 1,
#                         "original_amount": 200,
#                         "payment": 180,
#                         "cross_fee": 10,
#                         "orders": [
#                             {
#                                 "order_number": "ORD-002",
#                                 "original_amount": 200,
#                                 "final_price": 180,
#                                 "cross_fee": 10,
#                                 "out_admin": "root2"
#                             }
#                         ]
#                     }
#                 },
#                 "05-02": {
#                     "root2": {
#                         "order_count": 1,
#                         "original_amount": 150,
#                         "payment": 140,
#                         "cross_fee": 8,
#                         "orders": [
#                             {
#                                 "order_number": "ORD-003",
#                                 "original_amount": 150,
#                                 "final_price": 140,
#                                 "cross_fee": 8,
#                                 "out_admin": "root2"
#                             }
#                         ]
#                     }
#                 }
#             }
#             """
#
#         # 准备图表数据
#         all_dates = sorted(date_admin_data.keys())
#         # 获取字典中所有日期的数据（即外层字典的值）
#         # [
#         #     {"root1": {...}, "root2": {...}},    # 05-01的数据
#         #     {"root2": {...}}                     # 05-02的数据
#         # ]
#
#         all_admins = sorted({
#             admin for date_data in date_admin_data.values()
#             for admin in date_data.keys()
#         })
#
#         # 生成颜色映射（更鲜明的颜色）
#         admin_colors = {
#             admin: f'hsl({i * 360 / len(all_admins)}, 65%, 65%)'
#             for i, admin in enumerate(all_admins)
#         }
#
#         # 构建系列数据（每个圈子一个系列）
#         series = []
#         for admin in all_admins:
#             series_data = []
#             for date in all_dates:
#                 if admin in date_admin_data[date]:
#                     payment = date_admin_data[date][admin]['payment']
#                     cross_fee = date_admin_data[date][admin]['cross_fee']
#                     bill = payment + cross_fee
#                     series_data.append(bill)
#                 else:
#                     pass
#                     # series_data.append(0)  # 没有数据时显示0
#
#             series.append({
#                 'name': admin,
#                 'type': 'bar',
#                 'data': series_data,
#                 # 用于 自定义图表中数据系列（如柱状图的柱子、折线图的线条）的视觉样式。
#                 'itemStyle': {'color': admin_colors[admin]},
#                 # ECharts 的高亮交互样式配置，用于定义当用户悬停（hover）或点击图表中的数据项（如柱状图的柱子、折线图的点）时的视觉效果
#                 # shadowBlur: 10 表示高亮时会为数据项添加 模糊半径为 10 的阴影效果，使其看起来更突出
#                 'emphasis': {'itemStyle': {'shadowBlur': 10}},
#                 # 用于在图表中的数据项（如柱状图的柱子、折线图的点）上直接显示数值或其他信息
#                 'label': {
#                     'show': True,
#                     'position': 'top',
#                     'formatter': '{c}元'
#                 }
#             })
#
#         return JsonResponse({
#             "status": True,
#             "data": {
#                 "dates": all_dates,
#                 "series": series,
#                 "admins": all_admins,  # 新增：返回所有圈子列表
#                 "tooltip_data": date_admin_data,
#                 "colors": admin_colors
#             }
#         })
#
#     except Exception as e:
#         logger.error(f"其他圈子出库统计错误: {str(e)}", exc_info=True)
#         return JsonResponse({
#             "status": False,
#             "error": "数据加载失败",
#             "detail": str(e)
#         }, status=500)


