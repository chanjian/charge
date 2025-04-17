from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta
import logging
logger = logging.getLogger('web')

def get_date_fields(model):
    """获取模型中的所有日期/时间字段"""
    return [f.name for f in model._meta.get_fields()
            if isinstance(f, (models.DateField, models.DateTimeField))]


def filter_by_date_range(request, queryset):
    """
    通用日期范围筛选函数
    根据不同的输入条件（如指定的天数范围或手动输入的日期范围）来对查询集 queryset 进行日期过滤，并返回过滤后的查询集以及格式化后的开始日期字符串、结束日期字符串和日期字段信息
    返回: (queryset, start_date_str, end_date_str, date_fields)
    """
    # 获取当前时间（确保使用本地时区）
    now = timezone.localtime(timezone.now())
    # print(datetime.now())
    # print(timezone.now())
    # print(timezone.localtime(timezone.now()))
    today = now.date()
    print('today: ',today,type(today))

    # 1. 获取可用的日期字段
    date_fields = get_date_fields(queryset.model)
    logger.info("date_fields: %s", date_fields)
    print('date_fields: ',date_fields)
    date_field = request.GET.get('date_field', 'created_time')
    logger.info("date_fields: %s", date_field)
    print('date_field: ',date_field)

    # 2. 验证日期字段有效性
    if date_field not in date_fields:
        date_field = 'created_time'

    # 3. 处理日期范围
    start_date_str = request.GET.get('start_date')
    print('start_date_str: ',start_date_str)
    end_date_str = request.GET.get('end_date')
    print('end_date_str: ',end_date_str)
    days_range = request.GET.get('days_range')
    print('days_range: ',days_range)

    start_date = None
    end_date = None

    # 4. 如果有days_range参数，优先使用它计算日期范围
    if days_range:
        try:
            days = int(days_range)
            # end_date = today
            end_date = now
            print('end_date: ',end_date,type(end_date))
            start_date = end_date - timedelta(days=days-1)  # -1是为了包含当天
            print('start_date: ',start_date,type(start_date))
        except (ValueError, TypeError):
            pass
    elif start_date_str or end_date_str:
        # 4. 处理手动输入的日期
        if start_date_str:
            try:
                naive_start = datetime.strptime(start_date_str, '%Y-%m-%d')
                start_date = timezone.make_aware(naive_start)
                print('naive_start:::  ',naive_start)
                print('start_date:::  ', start_date)
            except ValueError:
                pass
        if end_date_str:
            try:
                naive_end = datetime.strptime(end_date_str, '%Y-%m-%d')
                # 把结束日期设为当天的 23:59:59
                end_of_day = naive_end.replace(hour=23, minute=59, second=59)
                end_date = timezone.make_aware(end_of_day)
                print('naive_end:::  ', naive_end)
                print('end_date::: ', end_date)
            except ValueError:
                pass
    else:
        start_date = now
        end_date = now

    # 5. 应用过滤
    if start_date:
        # 转换为时区感知的datetime（当天开始时刻00:00:00）
        start_datetime = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
        print('start_datetime--',start_datetime)
        # date_field 是变量，比如值是 "created_time"
        # f'{date_field}__gte' 生成字符串 "created_time__gte"
        # 构建字典 {"created_time__gte": start_date}
        # ** 解包后相当于直接写：queryset.filter(created_time__gte=start_date)
        queryset = queryset.filter(**{f'{date_field}__gte': start_datetime})
    if end_date:
        # 转换为时区感知的datetime（当天结束时刻23:59:59.999999）
        end_datetime = timezone.make_aware(datetime.combine(end_date, datetime.max.time()))
        print('end_datetime--', end_datetime)
        # next_day = end_date + timedelta(days=1)
        queryset = queryset.filter(**{f'{date_field}__lt': end_datetime})

    # 6. 返回格式化日期
    start_date_str = start_date.strftime('%Y-%m-%d') if start_date else ''
    print('start_date_str:::',start_date_str)
    end_date_str = end_date.strftime('%Y-%m-%d') if end_date else ''
    print('end_date_str:::', end_date_str)


    # return queryset, start_date_str, end_date_str, date_field
    return {
        'queryset':queryset,
        'start_date_str':start_date_str,
        'end_date_str':end_date_str,
        'date_field':date_field,
    }
