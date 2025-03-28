"""
URL configuration for SemiAutomaticChargeSystem project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from web.views import account,level,customer,gameorder,phoneorder,gamename,gamedenomination

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', account.login),  # 根路径重定向
    path('login/', account.login, name="login"),
    path('sms/login/', account.sms_login, name="sms_login"),
    path('sms/send/', account.sms_send, name="sms_send"),
    path('logout/', account.logout, name="logout"),
    path('home/', account.home, name="home"),
    path('order/',account.order,name='order'),

    path('level/list/', level.level_list, name="level_list"),
    path('level/add/', level.level_add, name="level_add"),
    path('level/edit/<int:pk>/', level.level_edit, name="level_edit"),
    path('level/delete/<int:pk>/', level.level_delete, name="level_delete"),
    #
    path('customer/list/',customer.customer_list,name='customer_list'),
    path('customer/add/',customer.customer_add,name='customer_add'),
    path('customer/edit/<int:pk>/',customer.customer_edit,name='customer_edit'),
    path('customer/delete/',customer.customer_delete,name='customer_delete'),
    path('customer/reset/<int:pk>/',customer.customer_reset,name='customer_reset'),
    path('customer/charge/<int:pk>/',customer.customer_charge,name='customer_charge'),
    path('customer/charge/<int:pk>/add/', customer.customer_charge_add, name="customer_charge_add"),
    path('customer/login/log/<int:pk>/',customer.customer_login_log,name='customer_login_log'),

    path('gameorder/list/',gameorder.gameorder_list,name='gameorder_list'),
    path('gameorder/add/',gameorder.gameorder_add,name='gameorder_add'),
    path('gameorder/edit/<int:pk>/',gameorder.gameorder_edit,name='gameorder_edit'),
    path('gameorder/delete/',gameorder.gameorder_delete,name='gameorder_delete'),
    path('gameorder/load-options/', gameorder.gameorder_load_charge_options, name='gameorder_load_charge_options'),

    path('gamename/list/',gamename.gamename_list,name='gamename_list'),
    path('gamename/add/',gamename.gamename_add,name='gamename_add'),
    path('gamename/edit/<int:pk>/',gamename.gamename_edit,name='gamename_edit'),
    path('gamename/delete/<int:pk>/',gamename.gamename_delete,name='gamename_delete'),

    path('gamedenomination/list/',gamedenomination.gamedenomination_list,name='gamedenomination_list'),
    path('gamedenomination/add/',gamedenomination.gamedenomination_add,name='gamedenomination_add'),
    path('gamedenomination/edit/<int:pk>/',gamedenomination.gamedenomination_edit,name='gamedenomination_edit'),
    path('gamedenomination/delete/<int:pk>/',gamedenomination.gamedenomination_delete,name='gamedenomination_delete'),


]
