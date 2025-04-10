from collections import defaultdict
from datetime import datetime
from utils.time_group import get_time_grouping
from django.db.models.functions import TruncDate, ExtractMonth, Coalesce
from django.shortcuts import render, redirect
from django.db.models import (
    Count, Sum, Q, F, Case, When, Value,
    IntegerField, DecimalField
)
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.utils.timezone import localtime

from utils.time_filter import filter_by_date_range
from web.models import TransactionRecord, GameOrder
from django.db.models import ExpressionWrapper
from django.utils import timezone
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
        queryset, start_str, end_str, date_field = filter_by_date_range(request, queryset)

        # for i in queryset:
        #     # print('123',i.created_time)
        #     local_time = timezone.localtime(i.created_time)
        #     print('123', local_time)

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


def chart_consumer(request):
    """消费者消费统计（按日期分组，显示所有消费者）"""
    try:
        current_admin = request.userinfo.get_root_admin()
        if not current_admin:
            return JsonResponse({"status": False, "error": "管理员不存在"}, status=400)

        queryset = GameOrder.objects.filter(
            order_status=2,
            consumer__parent__username=request.userinfo.username, # 筛选订单的消费者这个人的创建者是当前登录查看的管理员
            active=1,
            # created_by=current_admin  #逻辑有问题，这里指定了订单创建人是当前的管理员，如果用户自己创建的订单，筛选不出来
        ).select_related('consumer', 'recharge_option')

        # for i in queryset:
        #     # print('123',i.created_time)
        #     local_time = timezone.localtime(i.created_time)
        #     print('123', local_time,i.order_number)

        queryset, _, _, _ = filter_by_date_range(request, queryset)
        # for i in queryset:
        #     # print('123',i.created_time)
        #     local_time = timezone.localtime(i.created_time)
        #     print('123', local_time)

        # 获取所有有消费记录的消费者
        consumers = list(queryset.values_list(
            'consumer__username', flat=True
        ).distinct())

        # 按日期和消费者分组统计
        groups = queryset.annotate(
            date=TruncDate('created_time')
        ).values('date', 'consumer__username').annotate(
            final_amount=Coalesce(
                Sum(
                    F('recharge_option__amount') * F('consumer__level__percent') / 100,
                    output_field=DecimalField()
                ),
                Value(0, output_field=DecimalField())
            )
        ).order_by('date', 'consumer__username')

        # 获取所有日期
        dates = sorted(list(set(g['date'] for g in groups if g['date'])))
        print('dates:',dates)

        # 准备图表数据
        x_axis = [date.strftime('%m-%d') for date in dates]
        series = []

        for consumer in consumers:
            consumer_data = []
            for date in dates:
                # 查找该消费者在该日期的数据
                record = next((g for g in groups if g['date'] == date and g['consumer__username'] == consumer), None)
                consumer_data.append(float(record['final_amount']) if record else 0)

            # 只添加有消费记录的消费者
            if any(amount > 0 for amount in consumer_data):
                series.append({
                    "name": consumer,
                    "type": "bar",
                    "data": consumer_data,
                    "emphasis": {"focus": "series"}
                })

        # 获取详细订单数据（用于点击展示）
        order_details = {}
        for date in dates:
            date_str = date.strftime('%m-%d')
            order_details[date_str] = []

            date_orders = queryset.filter(
                created_time__date=date
            ).select_related('recharge_option', 'consumer')

            for order in date_orders:
                order_details[date_str].append({
                    "consumer": order.consumer.username,
                    "order_number": order.order_number,
                    "created_time": order.created_time if order.created_time else None,
                    "finished_time":order.finished_time if order.finished_time else None,
                    "amount": float(order.recharge_option.amount) if order.recharge_option else 0,
                    "discount": order.consumer.level.percent if order.consumer.level else 100,
                    "final_price": float(order.recharge_option.amount * order.consumer.level.percent / 100)
                    if order.recharge_option and order.consumer.level else 0
                })

        return JsonResponse({
            "status": True,
            "data": {
                "x_axis": x_axis,
                "series": series,
                "order_details": order_details
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
    """供应商统计（与客服风格一致）"""
    try:
        current_admin = request.userinfo.get_root_admin()
        if not current_admin:
            return JsonResponse({"status": False, "error": "管理员不存在"}, status=400)

        queryset = TransactionRecord.objects.filter(
            active=1,
            order__isnull=False,
            order__order_status=2,
            order__outed_by__usertype='SUPPLIER'
        ).select_related('order', 'order__outed_by', 'order__recharge_option')

        queryset, start_date, end_date, _ = filter_by_date_range(request, queryset)

        # 构建核心数据
        date_supplier_data = defaultdict(dict)
        for record in queryset.annotate(date=TruncDate('created_time')):
            date_str = record.date.strftime('%m-%d')
            supplier_name = record.order.outed_by.username

            if supplier_name not in date_supplier_data[date_str]:
                date_supplier_data[date_str][supplier_name] = {
                    'total': 0,
                    'payment': 0,
                    'orders': []  # 保留点击事件所需订单详情
                }

            date_supplier_data[date_str][supplier_name]['total'] += float(record.supplier_payment)
            date_supplier_data[date_str][supplier_name]['payment'] += float(record.supplier_payment)
            date_supplier_data[date_str][supplier_name]['orders'].append({
                'order_number': record.order.order_number,
                'amount': float(record.order.recharge_option.amount) if record.order.recharge_option else 0,
                'payment': float(record.supplier_payment),
                'created_time': record.created_time.strftime('%Y-%m-%d %H:%M') if record.created_time else None
            })

        # 处理数据
        all_dates = sorted(date_supplier_data.keys())
        all_suppliers = sorted({supplier for date_data in date_supplier_data.values() for supplier in date_data.keys()})

        supplier_colors = {
            supplier: f'hsl({i * 360 / len(all_suppliers)}, 50%, 65%)' # 饱和度50%，亮度65%
            for i, supplier in enumerate(all_suppliers)
        }

        # 构建系列数据
        series = []
        for supplier in all_suppliers:
            series_data = []
            for date in all_dates:
                if supplier in date_supplier_data[date]:
                    series_data.append(date_supplier_data[date][supplier]['total'])
                else:
                    series_data.append(None)

            series.append({
                'name': supplier,
                'type': 'bar',
                'data': series_data,
                'itemStyle': {'color': supplier_colors[supplier]}
            })

        return JsonResponse({
            "status": True,
            "data": {
                "dates": all_dates,
                "series": series,
                "tooltip_data": {  # 悬停数据
                    date: {
                        supplier: {
                            'total': data['total'],
                            'payment': data['payment'],
                            'order_count': len(data['orders'])  # ✅ 修正订单数计算
                        }
                        for supplier, data in date_data.items()
                    }
                    for date, date_data in date_supplier_data.items()
                },
                "details": {  # 点击事件数据
                    date: {
                        supplier: data['orders']
                        for supplier, data in date_data.items()
                    }
                    for date, date_data in date_supplier_data.items()
                },
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
    """客服统计（精确计算版）"""
    try:
        current_admin = request.userinfo.get_root_admin()
        if not current_admin:
            return JsonResponse({"status": False, "error": "管理员不存在"}, status=400)

        # 基础查询集
        queryset = TransactionRecord.objects.filter(
            active=1,
            order__isnull=False,
            order__order_status=2,
            order__outed_by__usertype='SUPPORT'
        ).select_related('order', 'order__outed_by', 'order__recharge_option')

        # 应用日期过滤
        queryset, start_date, end_date, _ = filter_by_date_range(request, queryset)

        # 构建核心数据结构
        date_support_data = defaultdict(dict)
        for record in queryset.annotate(date=TruncDate('created_time')):
            date_str = record.date.strftime('%m-%d')
            support_name = record.order.outed_by.username

            if support_name not in date_support_data[date_str]:
                date_support_data[date_str][support_name] = {
                    'support_payment': 0,  # 只计算垫付金额
                    'commission': 0,
                    'orders': []
                }

            # ✅ 精确累加各金额项
            date_support_data[date_str][support_name]['support_payment'] += float(record.support_payment)
            date_support_data[date_str][support_name]['commission'] += float(record.commission)
            date_support_data[date_str][support_name]['orders'].append({
                'order_number': record.order.order_number,
                'amount': float(record.order.recharge_option.amount) if record.order.recharge_option else 0,
                'support_payment': float(record.support_payment),
                'commission': float(record.commission),
                'created_time': record.created_time.strftime('%Y-%m-%d %H:%M') if record.created_time else None
            })

        # 处理数据
        all_dates = sorted(date_support_data.keys())
        all_supports = sorted({support for date_data in date_support_data.values() for support in date_data.keys()})

        # 生成颜色映射
        support_colors = {
            support: f'hsl({i * 360 / len(all_supports)}, 50%, 65%)'
            for i, support in enumerate(all_supports)
        }

        # 构建系列数据（只显示垫付金额）
        series = []
        for support in all_supports:
            series_data = []
            for date in all_dates:
                if support in date_support_data[date]:
                    series_data.append(date_support_data[date][support]['support_payment'])
                else:
                    series_data.append(None)  # 无数据点

            series.append({
                'name': support,
                'type': 'bar',
                'data': series_data,
                'itemStyle': {'color': support_colors[support]}
            })

        return JsonResponse({
            "status": True,
            "data": {
                "dates": all_dates,
                "series": series,
                "tooltip_data": {
                    date: {
                        support: {
                            'support_payment': data['support_payment'],
                            'commission': data['commission'],
                            'order_count': len(data['orders'])  # ✅ 准确计算订单数
                        }
                        for support, data in date_data.items()
                    }
                    for date, date_data in date_support_data.items()
                },
                "details": {  # 点击详情数据
                    date: {
                        support: data['orders']
                        for support, data in date_data.items()
                    }
                    for date, date_data in date_support_data.items()
                },
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


def chart_other_out_self(request):
    """其他圈子出库本圈订单统计（分组柱状图版）"""
    try:
        current_admin = request.userinfo.get_root_admin()
        if not current_admin:
            return JsonResponse({"status": False, "error": "管理员不存在"}, status=400)

        # 查询其他圈子出库到本圈的订单
        queryset = TransactionRecord.objects.filter(
            Q(from_user=current_admin) &  # 入库方是本圈
            ~Q(to_user=current_admin) &  # 出库方不是本圈
            Q(order__outed_by__isnull=False)  # 确保outed_by存在
        ).select_related(
            'order',
            'order__recharge_option',
            'order__outed_by',
            'order__consumer__level',
            'to_user'  # 关键修改：使用to_user作为出库方标识
        )

        # 应用日期过滤
        queryset, start_date, end_date, _ = filter_by_date_range(request, queryset)

        # 构建核心数据结构
        date_admin_data = defaultdict(lambda: defaultdict(lambda: {
            'order_count': 0,
            'original_amount': 0,
            'payment': 0,
            'cross_fee': 0,
            'orders': []
        }))

        for record in queryset:
            local_time = localtime(record.created_time)
            date_str = local_time.strftime('%m-%d')
            admin_name = record.to_user.username  # 关键修改：使用出库方名称

            # 获取出库人类型
            out_admin_type = record.order.outed_by.get_usertype_display() if record.order.outed_by else '未知'

            # 计算最终价格
            final_price = (record.order.recharge_option.amount *
                         record.order.consumer.level.percent / 100)

            # 累加统计数据
            date_admin_data[date_str][admin_name]['order_count'] += 1
            date_admin_data[date_str][admin_name]['original_amount'] += float(record.order.recharge_option.amount)
            date_admin_data[date_str][admin_name]['payment'] += float(final_price)
            date_admin_data[date_str][admin_name]['cross_fee'] += float(record.cross_fee)

            # 存储订单详情
            date_admin_data[date_str][admin_name]['orders'].append({
                'order_number': record.order.order_number,
                'original_amount': float(record.order.recharge_option.amount),
                'final_price': float(final_price),
                'cross_fee': float(record.cross_fee),
                'consumer': record.order.consumer.username,
                'out_admin': record.to_user.username,
                'out_admin_type': out_admin_type,
                'time': local_time.strftime('%Y-%m-%d %H:%M'),
                'order_status': record.order.get_order_status_display()
            })

        # 准备图表数据
        all_dates = sorted(date_admin_data.keys())
        all_admins = sorted({
            admin for date_data in date_admin_data.values()
            for admin in date_data.keys()
        })

        # 生成颜色映射（更鲜明的颜色）
        admin_colors = {
            admin: f'hsl({i * 360 / len(all_admins)}, 65%, 65%)'
            for i, admin in enumerate(all_admins)
        }

        # 构建系列数据（每个圈子一个系列）
        series = []
        for admin in all_admins:
            series_data = []
            for date in all_dates:
                if admin in date_admin_data[date]:
                    series_data.append(date_admin_data[date][admin]['payment'])
                else:
                    series_data.append(0)  # 没有数据时显示0

            series.append({
                'name': admin,
                'type': 'bar',
                'data': series_data,
                'itemStyle': {'color': admin_colors[admin]},
                'emphasis': {'itemStyle': {'shadowBlur': 10}},
                # 添加标签显示
                'label': {
                    'show': True,
                    'position': 'top',
                    'formatter': '{c}元'
                }
            })

        return JsonResponse({
            "status": True,
            "data": {
                "dates": all_dates,
                "series": series,
                "admins": all_admins,  # 新增：返回所有圈子列表
                "tooltip_data": date_admin_data,
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


def chart_self_out_other(request):
    """本圈出库其他圈子订单统计（完整版）"""
    try:
        current_admin = request.userinfo.get_root_admin()
        if not current_admin:
            return JsonResponse({"status": False, "error": "管理员不存在"}, status=400)

        # 查询本圈出库到其他圈子的订单
        queryset = TransactionRecord.objects.filter(
            Q(to_user=current_admin) &  # 出库方是本圈
            ~Q(from_user=current_admin) &  # 入库方不是本圈
            Q(order__outed_by__isnull=False)  # 确保outed_by存在
        ).select_related(
            'order',
            'order__recharge_option',
            'order__outed_by',
            'order__consumer__level',
            'to_user'
        )

        # 应用日期过滤
        queryset, start_date, end_date, _ = filter_by_date_range(request, queryset)

        # 构建核心数据结构
        date_admin_data = defaultdict(lambda: defaultdict(lambda: {
            'order_count': 0,
            'original_amount': 0,
            'receivable': 0,
            'cross_fee': 0,
            'orders': []
        }))

        for record in queryset:
            local_time = localtime(record.created_time)  # 转换为本地时区
            date_str = local_time.strftime('%m-%d')  # 使用本地时间格式化
            admin_name = record.from_user.username

            # 安全获取出库人类型
            out_admin_type = '未知'
            if record.order.outed_by:
                out_admin_type = record.order.outed_by.get_usertype_display()  # 使用get_xxx_display()方法

            # 计算对方圈子给消费者的最终价格
            final_price = (record.order.recharge_option.amount *
                         record.order.consumer.level.percent / 100)

            # 累加统计数据
            date_admin_data[date_str][admin_name]['order_count'] += 1
            date_admin_data[date_str][admin_name]['original_amount'] += float(record.order.recharge_option.amount)
            date_admin_data[date_str][admin_name]['receivable'] += float(final_price)
            date_admin_data[date_str][admin_name]['cross_fee'] += float(record.cross_fee)

            # 存储完整订单详情
            date_admin_data[date_str][admin_name]['orders'].append({
                'order_number': record.order.order_number,
                'original_amount': float(record.order.recharge_option.amount),
                'final_price': float(final_price),
                'cross_fee': float(record.cross_fee),
                'consumer': record.order.consumer.username,
                'in_admin': record.from_user.username,
                'out_admin_type': out_admin_type,
                'time': local_time.strftime('%Y-%m-%d %H:%M'),
                'order_status': record.order.get_order_status_display()
            })

        # 准备图表数据
        all_dates = sorted(date_admin_data.keys())
        all_admins = sorted({
            admin for date_data in date_admin_data.values()
            for admin in date_data.keys()
        })

        # 生成颜色映射
        # admin_colors = {
        #     admin: f'hsl({i * 360 / len(all_admins)}, 70%, 50%)'
        #     for i, admin in enumerate(all_admins)
        # }
        # ✅ 修改后的颜色生成（柔和的蓝绿色系）
        admin_colors = {
            admin: f'hsl({180 + i * 60 % 360}, 40%, 70%)'  # 从绿色(120°)开始，间隔60°
            for i, admin in enumerate(all_admins)
        }

        # 构建系列数据
        series = []
        for admin in all_admins:
            series_data = []
            for date in all_dates:
                if admin in date_admin_data[date]:
                    series_data.append(date_admin_data[date][admin]['receivable'])
                else:
                    series_data.append(None)

            series.append({
                'name': admin,
                'type': 'bar',
                'data': series_data,
                'itemStyle': {'color': admin_colors[admin]},
                'emphasis': {'itemStyle': {'shadowBlur': 10}}
            })

        return JsonResponse({
            "status": True,
            "data": {
                "dates": all_dates,
                "series": series,
                "tooltip_data": {
                    date: {
                        admin: {
                            'order_count': data['order_count'],
                            'original_amount': data['original_amount'],
                            'receivable': data['receivable'],
                            'cross_fee': data['cross_fee']
                        }
                        for admin, data in date_data.items()
                    }
                    for date, date_data in date_admin_data.items()
                },
                "details": {
                    date: {
                        admin: data['orders']
                        for admin, data in date_data.items()
                    }
                    for date, date_data in date_admin_data.items()
                },
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