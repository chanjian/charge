from django.http import QueryDict
from django.template import Library
from django.conf import settings
from django.urls import reverse
from django.utils.safestring import mark_safe

register = Library()


def check_permission(request, name):
    # print(request, name, args, kwargs)
    # 1.获取当前登录用户的角色
    usertype = request.userdict.usertype

    # 2.根据角色获取他所有的权限字典
    permission_dict = settings.PERMISSION[usertype]

    if name in permission_dict:
        return True

    if name in settings.PERMISSION_PUBLIC:
        return True


@register.simple_tag
def add_permission(request, name, *args, **kwargs):
    # 4.无权限，返回空
    if not check_permission(request, name):
        return ""

    # 5.有权限，通过"customer_add"反向生成URL
    url = reverse(name, args=args, kwargs=kwargs)
    tpl = """
    <a href="{}" class="btn btn-success">
            <span class="glyphicon glyphicon-plus-sign"></span> 新建
    </a>
    """.format(url)
    return mark_safe(tpl)


@register.simple_tag
def edit_permission(request, name, *args, **kwargs):
    # 4.无权限，返回空
    if not check_permission(request, name):
        return ""

    # 5.有权限，通过"customer_add"反向生成URL
    # /customer/edit/11/
    url = reverse(name, args=args, kwargs=kwargs)

    param = request.GET.urlencode()
    print(param)
    # 根据当前用户请求获取GET参数
    param = request.GET.urlencode()
    if param:
        new_query_dict = QueryDict(mutable=True)
        new_query_dict['_filter'] = param
        filter_string = new_query_dict.urlencode()
        tpl = """<a href="{}?{}" class="btn btn-primary btn-xs">编辑</a>""".format(url, filter_string)
        return mark_safe(tpl)

    tpl = """<a href="{}" class="btn btn-primary btn-xs">编辑</a>""".format(url)
    return mark_safe(tpl)


@register.simple_tag
def delete_permission(request, name, *args, **kwargs):
    # 4.无权限，返回空
    if not check_permission(request, name):
        return ""


    # 5.有权限，通过"customer_add"反向生成URL
    pk = kwargs.get('pk')
    tpl = """
    <a cid="{}" class="btn btn-danger btn-xs btn-delete">删除</a>
    """.format(pk)
    return mark_safe(tpl)


@register.simple_tag
def delete_url_permission(request, name, *args, **kwargs):
    # 4.无权限，返回空
    if not check_permission(request, name):
        return ""

    # 5.有权限，通过"customer_add"反向生成URL
    # pk = kwargs.get('pk')
    # tpl = """
    # <a cid="{}" class="btn btn-danger btn-xs btn-delete">删除</a>
    # """.format(pk)
    # return mark_safe(tpl)

    url = reverse(name, args=args, kwargs=kwargs)
    tpl = """
    <a href="{}" class="btn btn-danger btn-xs btn-delete">删除</a>
    """.format(url)
    return mark_safe(tpl)


@register.filter
def has_permission(request, others):
    name_list = others.split(',')
    for name in name_list:
        status = check_permission(request, name)
        if status:
            return True
    return False


@register.simple_tag
def out_permission(request, name, *args, **kwargs):
    # 4.无权限，返回空
    if not check_permission(request, name):
        return ""

    # 5.有权限，通过"customer_add"反向生成URL
    url = reverse(name, args=args, kwargs=kwargs)
    tpl = """
    <a href="{}?qb_discount={{ request.GET.qb_discount }}" class="btn btn-xs btn-warning" onclick="return confirm('确认出库吗？')">出库
    </a>
    """.format(url)
    return mark_safe(tpl)
