from django.utils import timezone
from datetime import timedelta
from utils.pager import Pagination

def filter_by_date_range(request, queryset):
    """
    根据请求中的日期范围或天数范围过滤查询集
    :param request: 请求对象
    :param queryset: 原始查询集
    :return: 过滤后的查询集, start_date, end_date
    """
    # 获取查询参数
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    days_range = request.GET.get('days_range')

    # 根据动态范围计算日期区间
    if days_range:
        days_range = int(days_range)
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days_range)
    else:
        # 将字符串日期转换为带时区的 datetime 对象
        if start_date and end_date:
            start_date = timezone.make_aware(
                timezone.datetime.strptime(start_date, '%Y-%m-%d')
            )
            end_date = timezone.make_aware(
                timezone.datetime.strptime(end_date, '%Y-%m-%d')
            )
        else:
            start_date = None
            end_date = None

    # 根据日期筛选数据
    if start_date and end_date:
        queryset = queryset.filter(create_datetime__range=(start_date, end_date))

    start_date = start_date.strftime('%Y-%m-%d') if start_date else '',
    end_date = end_date.strftime('%Y-%m-%d') if end_date else '',

    pager = Pagination(request, queryset)

    return queryset, start_date, end_date, pager
