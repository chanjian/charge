from django import template
from django.utils.html import escape
import difflib

register = template.Library()

@register.filter
def mul(value, arg):
    """乘法过滤器"""
    return float(value) * float(arg)


