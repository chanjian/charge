from django.template import Library
from django.conf import settings
import copy

register = Library()


@register.inclusion_tag('tag/nb_menu.html')
def nb_menu(request):
    # 1.读取当前用户的角色信息
    print(request.userdict.usertype)

    # 2.读取当前用户拥有权限的菜单
    user_menu_dict = copy.deepcopy(settings.NB_MENU[request.userdict.usertype])

    for item in user_menu_dict:
        item['class'] = 'hide'
        for child in item['children']:
            # if child['url'] == request.path_info:   #v1版本
            if child['name'] == request.userdict.menu_name:    #v2版本
                child['class'] = 'active'
                item['class'] = ''
    return {'menu_list': user_menu_dict}
