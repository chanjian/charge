from django.http import QueryDict
from django.template import Library
from django.conf import settings
from django.urls import reverse
from django.utils.safestring import mark_safe
from web import models

register = Library()


@register.filter
def color(num):
    return models.TransactionRecord.charge_type_class_mapping[num]
