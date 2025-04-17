from django.db.models import Q
from django.shortcuts import render
from web import models
from utils.pager import Pagination
from utils.time_filter import filter_by_date_range

def transaction_list(request):
    """我的交易记录"""

    if request.userinfo.usertype == 'CUSTOMER':
        queryset = models.TransactionRecord.objects.filter(customer_id=request.userinfo.id,active=1).order_by('-id')
    elif request.userinfo.usertype in ['SUPPORT','SUPPLIER']:
        queryset = models.TransactionRecord.objects.filter(order__outed_by__username=request.userinfo.username, active=1).order_by('-id')
    elif request.userinfo.usertype == 'ADMIN':
        queryset = models.TransactionRecord.objects.filter(order__outed_by__parent__username=request.userinfo.username).order_by('-id')
    else:
        queryset = models.TransactionRecord.objects.filter(active=1).order_by('-id')

    keyword = request.GET.get('keyword', '').strip()
    con = Q()
    if keyword:
        con.connector = 'OR'
        con.children.append(('order__order_number__contains', keyword))
        queryset = queryset.filter(con)

    # # 调用封装好的函数进行日期过滤
    # queryset, start_date, end_date, _ = filter_by_date_range(request, queryset)
    # 日期过滤
    package = filter_by_date_range(request, queryset)
    queryset = package.pop('queryset')

    pager = Pagination(request, queryset)


    context = {
        **package,
        'pager':pager,
        'keyword':keyword,
        'date_field': request.GET.get('date_field', 'created_time'),
    }
    # print(start_date,end_date,queryset)
    return render(request,'transaction_list.html',context)
    # return render(request, 'transaction_list.html', locals())
