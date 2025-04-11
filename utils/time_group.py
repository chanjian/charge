from django.db.models.functions import TruncDate, TruncHour

def get_time_grouping(start_str, end_str, date_field):
    """
    根据日期范围返回分组方式和时间格式
    :return: (group_expression, time_format)
    """
    if start_str and end_str and start_str == end_str:
        return TruncHour(date_field), '%H:%M'  # 按小时分组
    return TruncDate(date_field), '%m-%d'     # 按天分组