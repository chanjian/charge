from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SemiAutomaticChargeSystem.settings')

app = Celery('SemiAutomaticChargeSystem')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related config keys should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()



from celery.schedules import crontab


app.conf.beat_schedule = {
    'check-timeout-orders-every-hour': {
        'task': 'web.tasks.check_orders_timeout',
        'schedule': crontab(minute=52),  # 每小时整点执行
    },
}

# 使用这个命令启动
# celery -A SemiAutomaticChargeSystem.celery  worker --loglevel=info --pool=solo

# 使用这个启动定时任务
# celery -A SemiAutomaticChargeSystem.celery beat -l debug