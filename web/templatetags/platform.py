# yourapp/templatetags/order_tags.py
from django import template

register = template.Library()

@register.filter
def should_display_field(field, form_initial):
    platform = form_initial.get('platform', '')
    if field.name == 'recharge_option' and platform == 'ANDROID':
        return 'none'
    elif field.name == 'custom_amount' and platform == 'IOS':
        return 'none'
    return 'block'