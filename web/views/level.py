from django.conf import settings
from django.shortcuts import render, redirect,HttpResponse
from django.urls import reverse
from utils.link import filter_reverse
from web import models
from django import forms
from utils.bootstrap import BootStrapForm
from django.contrib import messages
from django.contrib.messages.api import get_messages
import logging
logger = logging.getLogger('web')



class LevelForm(forms.Form):
    title = forms.CharField(
        label='标题',
        required=True,
        widget=forms.TextInput(attrs={'class':'form-control','placeholder':'请输入标题'}),
    )

    percent = forms.CharField(
        label='折扣',
        required=True,
        widget=forms.TextInput(attrs={'class':'form-control','placeholder':'请输入折扣'}),
    )


def level_list(request):
    messages = get_messages(request)
    for msg in messages:
        print(msg)

    queryset = models.Level.objects.filter(active=1,creator_id=request.userdict.id)
    # queryset_customer = models.Level.objects.filter(active=1,level_type='CUSTOMER')
    # queryset_supplier = models.Level.objects.filter(active=1, level_type='SUPPLIER')
    queryset_customer = queryset.filter(active=1, level_type='CUSTOMER')
    queryset_supplier = queryset.filter(active=1, level_type='SUPPLIER')
    context = {
        'queryset_customer':queryset_customer,
        'queryset_supplier':queryset_supplier,
    }
    return render(request,'level_list.html',context)

# class LevelModelForm(BootStrapForm,forms.ModelForm):
#     class Meta:
#         model = models.Level
#         fields = ['title','percent','level_type']
#
#     def clean(self):
#         cleaned_data = super().clean()
#         title = cleaned_data.get('title')
#         percent = cleaned_data.get('percent')
#         level_type = cleaned_data.get('level_type')
#
#         if not all([title, percent, level_type]):
#             return cleaned_data  # 基础校验失败时跳过
#
#         # 检查是否已存在相同 title + level_type 或 percent + level_type 的记录
#         queryset = models.Level.objects.filter(
#             models.Q(title=title, level_type=level_type,active=1) |
#             models.Q(percent=percent, level_type=level_type,active=1)
#         )
#         if self.instance.pk:  # 编辑时排除自身
#             queryset = queryset.exclude(pk=self.instance.pk)
#
#         if queryset.exists():
#             # 根据冲突字段提示不同错误
#             if models.Level.objects.filter(title=title, level_type=level_type,active=1).exists():
#                 raise forms.ValidationError(f"等级名称 '{title}' 在该等级类型下已存在！")
#             else:
#                 raise forms.ValidationError(f"折扣 {percent}% 在该等级类型下已存在！")
#
#
#         return cleaned_data

  # def validate_unique(self):
    #     pass  # 禁用默认验证，完全依赖模型的 clean()

class LevelModelForm(BootStrapForm, forms.ModelForm):
    class Meta:
        model = models.Level
        fields = ['title', 'percent', 'level_type']

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        title = cleaned_data.get('title')
        percent = cleaned_data.get('percent')
        level_type = cleaned_data.get('level_type')

        if not all([title, percent, level_type]):
            return cleaned_data

        # 如果是编辑现有实例，获取creator
        creator = self.instance.creator if self.instance.pk else self.request.userdict.id

        # 检查当前管理员是否已创建相同等级
        queryset = models.Level.objects.filter(creator=creator,active=1,level_type=level_type).filter(models.Q(title=title) | models.Q(percent=percent))

        if self.instance.pk:  # 编辑时排除自身
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            if queryset.filter(title=title).exists():
                raise forms.ValidationError(f"您已创建过名称为'{title}'的{level_type}等级")
            else:
                raise forms.ValidationError(f"您已创建过折扣为{percent}%的{level_type}等级")

        return cleaned_data



# def level_add(request):
#     if request.method == 'GET':
#         form = LevelModelForm()
#
#         return render(request,'form.html',{'form':form})
#
#     form = LevelModelForm(data=request.POST)
#     if not form.is_valid():
#
#         return render(request, 'form.html', {'form':form})
#     form.instance.creator = request.userinfo
#     form.save()
#     return redirect(reverse('level_list'))

def level_add(request):
    if request.method == 'GET':
        form = LevelModelForm(request=request)
        return render(request, 'form.html', {'form': form})

    form = LevelModelForm(data=request.POST, request=request)  # 传入request
    if not form.is_valid():
        return render(request, 'form.html', {'form': form})
    form.instance.creator = request.userinfo
    form.save()
    return redirect(reverse('level_list'))



def level_edit(request,pk):
    level_object = models.Level.objects.filter(id=pk,active=1).first()
    if request.method == 'GET':
        form = LevelModelForm(instance=level_object)
        return render(request, 'form.html', {'form': form})
    form = LevelModelForm(data=request.POST,instance=level_object)
    if not form.is_valid():
        return render(request, 'form.html', {'form': form})
    form.save()
    return redirect(filter_reverse(request,'/level/list/'))

# def level_delete(request,pk):
#     # 检查是否有用户关联该等级
#     exists = models.UserInfo.objects.filter(level_id=pk).exists()
#     if not exists:
#         models.Level.objects.filter(id=pk).update(active=0)
#     return redirect(reverse('level_list'))


def level_delete(request, pk):
    # 1. 获取要删除的等级
    try:
        level = models.Level.objects.get(id=pk, active=1)
    except models.Level.DoesNotExist:
        messages.add_message(request, settings.MESSAGE_DANGER_TAG , "等级不存在或已被删除")
        return redirect('level_list')

    # 2. 权限验证
    if request.userdict.usertype != 'SUPERADMIN' and level.creator.id != request.userinfo.id:
        messages.add_message(request,settings.MESSAGE_DANGER_TAG , "您只能删除自己创建的等级")
        return redirect('level_list')

    # 3. 检查等级是否被使用
    if models.UserInfo.objects.filter(level=level).exists():
        messages.add_message(request, settings.MESSAGE_DANGER_TAG ,"该等级已被关联用户，无法删除")
        return redirect('level_list')

    # 4. 执行软删除
    level.active = 0
    level.save()
    messages.add_message(request, 25 ,f"等级 {level.title} 已删除")  #25对应success

    return redirect(reverse('level_list'))