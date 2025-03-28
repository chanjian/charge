import os
import sys
import django

# 将项目根目录添加到 Python 路径
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# 必须在所有 Django 导入之前设置环境变量
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "SemiAutomaticChargeSystem.settings")
django.setup()

# 现在可以安全导入 Django 模块
from django.contrib.sessions.backends.cache import SessionStore
from django.core.cache import cache

session_key = "ernk70qfe3f6edx4kbqirs1vjw7pk23l"
session = SessionStore(session_key=session_key)
decoded_data = session.load()
print(decoded_data)