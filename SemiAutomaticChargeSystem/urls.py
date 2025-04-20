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
from web.views import account, level, customer, gameorder, phoneorder, gamename, gamedenomination, dashboard, chart, \
    policy, transaction

from django.conf import settings
from django.urls import path, re_path
from django.views.static import serve

urlpatterns = [
    # re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}, name='media'),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}, name='media'),

    path('admin/', admin.site.urls),
    path('', account.login),  # 根路径重定向
    path('login/', account.login, name="login"),
    path('sms/login/', account.sms_login, name="sms_login"),
    path('sms/send/', account.sms_send, name="sms_send"),
    path('logout/', account.logout, name="logout"),
    path('home/', account.home, name="home"),

    path('image/code/', account.image_code,name='image_code'),
    path('profile/', account.profile, name='profile'),

    path('crossfee/manage/',account.crossfee_manage,name='crossfee_manage'),
    path('crossfee/clear/',account.crossfee_clear,name='crossfee_clear'),

    path('policy/list/', policy.policy_list, name="policy_list"),
    path('policy/add/', policy.policy_add, name="policy_add"),
    path('policy/edit/<int:pk>/', policy.policy_edit, name="policy_edit"),
    path('policy/delete/', policy.policy_delete, name="policy_delete"),
    path('policy/upload/',policy.policy_upload,name='policy_upload'),
    path('policy/example/download/', policy.policy_example_download, name='policy_example_download'),

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

    path('gameorder/alllist/',gameorder.gameorder_alllist,name='gameorder_alllist'),
    path('gameorder/list/',gameorder.gameorder_list,name='gameorder_list'),
    path('gameorder/finished/list/',gameorder.gameorder_finished_list,name='gameorder_finished_list'),
    path('gameorder/deleted/list/',gameorder.gameorder_deleted_list,name='gameorder_deleted_list'),
    path('gameorder/timeout/list/',gameorder.gameorder_timeout_list,name='gameorder_timeout_list'),
    path('gameorder/add/',gameorder.gameorder_add,name='gameorder_add'),
    path('gameorder/edit/<int:pk>/',gameorder.gameorder_edit,name='gameorder_edit'),
    path('gameorder/delete/',gameorder.gameorder_delete,name='gameorder_delete'),
    path('gameorder/load-options/', gameorder.gameorder_load_charge_options, name='gameorder_load_charge_options'),
    path('gameorder/edit/log/<int:pk>/', gameorder.gameorder_edit_log, name='gameorder_edit_log'),
    path('gameorder/out/<int:pk>',gameorder.gameorder_out,name='gameorder_out'),

    path('gamename/list/',gamename.gamename_list,name='gamename_list'),
    path('gamename/add/',gamename.gamename_add,name='gamename_add'),
    path('gamename/edit/<int:pk>/',gamename.gamename_edit,name='gamename_edit'),
    path('gamename/delete/<int:pk>/',gamename.gamename_delete,name='gamename_delete'),


    path('gamedenomination/list/',gamedenomination.gamedenomination_list,name='gamedenomination_list'),
    path('gamedenomination/add/',gamedenomination.gamedenomination_add,name='gamedenomination_add'),
    path('gamedenomination/edit/<int:pk>/',gamedenomination.gamedenomination_edit,name='gamedenomination_edit'),
    path('gamedenomination/delete/<int:pk>/',gamedenomination.gamedenomination_delete,name='gamedenomination_delete'),

    # path('chart/list/', chart.chart_list, name='chart_list'),
    path('dashboard/',chart.dashboard_list,name="dashboard_list"),
    path('chart/bar/', chart.chart_bar,name='chart_bar'),
    path('chart/consumer/', chart.chart_consumer, name='chart_consumer'),
    path('chart/supplier/', chart.chart_supplier, name='chart_supplier'),
    path('chart/support/', chart.chart_support, name='chart_support'),
    path('chart/self/out/other',chart.chart_self_out_other,name='chart_self_out_other'),
    path('chart/other/out/self',chart.chart_other_out_self,name='chart_other_out_self'),


    path('transaction/list/',transaction.transaction_list,name='transaction_list'),

]

from django.conf.urls.static import static
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# from django.views.static import serve
# if settings.DEBUG:
#     urlpatterns += [
#         path('media/<path:path>', serve, {'document_root': settings.MEDIA_ROOT}),  # 显式媒体文件路由
#         path('static/<path:path>', serve, {'document_root': settings.STATIC_ROOT}),  # 显式静态文件路由
#     ]
