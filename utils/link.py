def filter_reverse(request,url):
    #1.获取filter
    filter_string = request.GET.get('_filter')
    if not filter_string:
        return url
    #2.url拼接
    return url+"?{}".format(filter_string)