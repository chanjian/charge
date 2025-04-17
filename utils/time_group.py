from django.db.models.functions import TruncHour, TruncDate
from django.utils import timezone
from datetime import timedelta

def get_time_grouping(start_str, end_str, date_field):
    """
    强制按小时分组，但保持日期范围不变
    :return: (TruncHour表达式, 时间格式, 是否显示全天小时刻度)
    """
    return TruncHour(date_field), '%H:%M', True