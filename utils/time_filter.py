from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta


def get_date_fields(model):
    """获取模型中的所有日期/时间字段"""
    return [f.name for f in model._meta.get_fields()
            if isinstance(f, (models.DateField, models.DateTimeField))]


def filter_by_date_range(request, queryset):
    """
    通用日期范围筛选函数
    返回: (queryset, start_date_str, end_date_str, date_fields)
    """
    # 获取当前时间（确保使用本地时区）
    now = timezone.localtime(timezone.now())
    today = now.date()

    # 1. 获取可用的日期字段
    date_fields = get_date_fields(queryset.model)
    date_field = request.GET.get('date_field', 'created_time')

    # 2. 验证日期字段有效性
    if date_field not in date_fields:
        date_field = 'created_time'

    # 3. 处理日期范围
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    days_range = request.GET.get('days_range')

    start_date = None
    end_date = None

    # 4. 如果有days_range参数，优先使用它计算日期范围
    if days_range:
        try:
            days = int(days_range)
            end_date = today
            print('end_date',end_date)
            start_date = end_date - timedelta(days=days-1)  # -1是为了包含当天
        except (ValueError, TypeError):
            pass
    else:
        # 5. 处理手动输入的日期范围
        if start_date_str:
            try:
                naive_start = datetime.strptime(start_date_str, '%Y-%m-%d')
                start_date = timezone.datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        if end_date_str:
            try:
                naive_end = datetime.strptime(end_date_str, '%Y-%m-%d')
                end_date = timezone.datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                pass

    # 6. 应用日期过滤
    if start_date:
        # 转换为时区感知的datetime（当天开始时刻）
        start_datetime = timezone.make_aware(
            datetime.combine(start_date, datetime.min.time())
        )
        queryset = queryset.filter(**{f'{date_field}__gte': start_date})

    if end_date:
        # 转换为时区感知的datetime（当天结束时刻）
        end_datetime = timezone.make_aware(
            datetime.combine(end_date, datetime.max.time())
        )
        # end_date += timedelta(days=1)  # 包含结束当天
        queryset = queryset.filter(**{f'{date_field}__lt': end_datetime})

    # 7. 返回格式化日期字符串
    start_str = start_date.strftime('%Y-%m-%d') if start_date else ''
    # end_str = (end_date - timedelta(days=1)).strftime('%Y-%m-%d') if end_date else ''
    end_str = end_date.strftime('%Y-%m-%d') if end_date else ''

    # return queryset, start_str, end_str, date_fields
    return queryset, start_str, end_str, date_field