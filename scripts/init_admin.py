# 启动django
import os
import sys
import django

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(base_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SemiAutomaticChargeSystem.settings')
django.setup()  # 伪造让django启动

from web import models
from utils.encrypt import md5

models.UserInfo.objects.create(username='root10',usertype='ADMIN',password=md5("123"), mobile="16645462585652")

