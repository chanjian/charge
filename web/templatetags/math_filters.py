# web/templatetags/math_filters.py
from django import template
from decimal import Decimal

register = template.Library()

@register.filter(name='absolute')  # 使用不同的名称
def absolute_value(value):
    """安全的绝对值过滤器"""
    try:
        return abs(Decimal(str(value)))
    except (ValueError, TypeError):
        return value


@register.filter(name='mul')
def mul(value, arg):
    """Multiply the value by the arg"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return ''


@register.filter(name='div')
def div(value, arg):
    """除法过滤器"""
    return value / arg