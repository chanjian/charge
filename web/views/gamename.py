from django.conf import settings
from django.urls import reverse

from web import models
from utils.bootstrap import BootStrapForm,BootStrapModelForm
from utils.encrypt import md5
from django.contrib import messages
from django.contrib.messages.api import get_messages
from web.models import GameOrder,TransactionRecord
from django.shortcuts import render, redirect
import logging
logger = logging.getLogger('web')


def gamename_list(request):
    queryset = models.GameName.objects.filter(active=1).all()
    context = {
        'queryset':queryset,
    }
    print(queryset)
    return render(request,'gamename_list.html',context)


class GameNameAddModelForm(BootStrapModelForm):
    class Meta:
        model = models.GameName
        exclude = ['active']

def gamename_add(request):
    if request.method == 'GET':
        form = GameNameAddModelForm()
        return render(request,'form.html',{'form':form})
    form = GameNameAddModelForm(data=request.POST)
    if not form.is_valid():
        return render(request,'form.html',{'form':form})
    form.save()
    return redirect('gamename_list')


def gamename_edit(request,pk):
    gamename_object = models.GameName.objects.filter(id=pk,active=1).first()
    if request.method == 'GET':
        form = GameNameAddModelForm(instance=gamename_object)
        return render(request, 'form.html', {'form': form})
    form = GameNameAddModelForm(data=request.POST,instance=gamename_object)
    if not form.is_valid():
        return render(request, 'form.html', {'form': form})
    form.save()
    # return redirect('gamename_list')
    from utils.link import filter_reverse
    return redirect(filter_reverse(request, '/gamename/list/'))


def gamename_delete(request,pk):
    # 1. 获取要删除的等级
    try:
        gamename = models.GameName.objects.get(id=pk, active=1)
    except models.GameName.DoesNotExist:
        messages.add_message(request, settings.MESSAGE_DANGER_TAG, "等级不存在或已被删除")
        return redirect('gamename_list')

    # 2. 权限验证
    if request.userdict.usertype != 'SUPERADMIN':
        messages.add_message(request, settings.MESSAGE_DANGER_TAG, "只有超级管理员才有权限删除此条数据")
        return redirect('gamename_list')

    # 3. 检查等级是否被使用
    if models.GameOrderOption.objects.filter(game=gamename).exists():
        messages.add_message(request, settings.MESSAGE_DANGER_TAG, "该游戏名称已经关联相对应的游戏档位，无法删除。您可以删除对应的游戏档位后再删除此游戏名称")
        return redirect('gamename_list')

    # 4. 执行软删除
    gamename.active = 0
    gamename.save()
    messages.add_message(request, 25, f"等级 {gamename.name} 已删除")  # 25对应success

    return redirect(reverse('gamename_list'))

