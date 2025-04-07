from django.db import models
from django.utils import timezone
from datetime import timedelta


def get_date_fields(model):
    """获取模型中的所有日期/时间字段"""
    return [f.name for f in model._meta.get_fields()
            if isinstance(f, (models.DateField, models.DateTimeField))]


def filter_by_date_range(request, queryset):
    """
    通用日期范围筛选函数
    返回: (queryset, start_date_str, end_date_str)
    """
    # 1. 获取可用的日期字段
    date_fields = get_date_fields(queryset.model)
    date_field = request.GET.get('date_field', 'created_time')

    # 2. 验证日期字段有效性
    if date_field not in date_fields:
        date_field = 'created_time'

    # 3. 处理日期范围
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    # 4.应用日期过滤
    if start_date:
        try:
            start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
            queryset = queryset.filter(**{f'{date_field}__gte': start_date})
        except ValueError:
            pass

    if end_date:
        try:
            end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
            end_date += timedelta(days=1)  # 包含结束当天
            queryset = queryset.filter(**{f'{date_field}__lt': end_date})
        except ValueError:
            pass

    # 5. 返回格式化日期字符串
    start_str = start_date.strftime('%Y-%m-%d') if start_date else ''
    end_str = (end_date - timedelta(days=1)).strftime('%Y-%m-%d') if end_date else ''

    return queryset, start_str, end_str, date_field