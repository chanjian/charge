from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    """乘法过滤器"""
    return float(value) * float(arg)