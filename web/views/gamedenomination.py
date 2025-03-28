from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect ,HttpResponse
from django.db import transaction
from django.urls import reverse

from utils.link import filter_reverse
from utils.pager import Pagination
from utils.response import BaseResponse
from web import models
from utils.bootstrap import BootStrapForm,BootStrapModelForm
from utils.encrypt import md5
from django.contrib import messages
from django.contrib.messages.api import get_messages
from web.models import GameOrder,GameDenomination,TransactionRecord
import logging
logger = logging.getLogger('web')


def gamedenomination_list(request):
    queryset = models.GameDenomination.objects.filter(active=1).all()
    context = {
        'queryset': queryset,
    }
    print(queryset)
    return render(request, 'gamedenomination_list.html', context)

class GameDenominationAddModelForm(BootStrapModelForm):
    class Meta:
        model = models.GameDenomination
        exclude = ['active']

def gamedenomination_add(request):
    if request.method == 'GET':
        form = GameDenominationAddModelForm()
        return render(request, 'form.html', {'form': form})
    form = GameDenominationAddModelForm(data=request.POST)
    if not form.is_valid():
        return render(request, 'form.html', {'form': form})
    form.save()
    return redirect('gamedenomination_list')


def gamedenomination_edit(request,pk):
    gamedenomination_object = models.GameDenomination.objects.filter(id=pk, active=1).first()
    if request.method == 'GET':
        form = GameDenominationAddModelForm(instance=gamedenomination_object)
        return render(request, 'form.html', {'form': form})
    form = GameDenominationAddModelForm(data=request.POST, instance=gamedenomination_object)
    if not form.is_valid():
        return render(request, 'form.html', {'form': form})
    form.save()
    # return redirect('gamename_list')
    from utils.link import filter_reverse
    return redirect(filter_reverse(request, '/gamedenomination/list/'))


def gamedenomination_delete(request,pk):
    # 1. 获取要删除的等级
    try:
        gamedenomination = models.GameDenomination.objects.get(id=pk, active=1)
    except models.GameDenomination.DoesNotExist:
        messages.add_message(request, settings.MESSAGE_DANGER_TAG, "等级不存在或已被删除")
        return redirect('gamedenomination_list')

    # 2. 权限验证
    if request.userdict.usertype != 'SUPERADMIN':
        messages.add_message(request, settings.MESSAGE_DANGER_TAG, "只有超级管理员才有权限删除此条数据")
        return redirect('gamedenomination_list')

    # # 3. 检查等级是否被使用
    # if models.GameDenomination.objects.filter(game=gamedenomination).exists():
    #     messages.add_message(request, settings.MESSAGE_DANGER_TAG,
    #                          "该游戏名称已经关联相对应的游戏档位，无法删除。您可以删除对应的游戏档位后再删除此游戏名称")
    #     return redirect('gamedenomination_list')

    # 4. 执行软删除
    gamedenomination.active = 0
    gamedenomination.save()
    messages.add_message(request, 25, f"{gamedenomination.game}的{gamedenomination.platform}系统的{gamedenomination.amount}档位已成功删除")  # 25对应success

    return redirect(reverse('gamedenomination_list'))