"""
Django settings for SemiAutomaticChargeSystem project.

Generated by 'django-admin startproject' using Django 5.1.7.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-t(pn-!g7pnh3r)vj8)%a4rj7^stwi%v2w-^lyql^kd*s3m=^5-'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'web',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'web.middleware.loginmiddleware.AuthMiddleware'
]

ROOT_URLCONF = 'SemiAutomaticChargeSystem.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates']
        ,
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'SemiAutomaticChargeSystem.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'zh-hans'

TIME_ZONE = 'Asia/Shanghai'  # 设置默认时区为北京时间

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = '/static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# cache缓存
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://127.0.0.1:6379",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 100},
            "PASSWORD": "chanjian8888",
        }
    }
}

# session配置
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7


LOGIN_HOME = "/level/list/"

SESSION_KEY = "userinfo"
LOGIN_URL = "/login/"

WHITE_URL = [
    '/login/',
    '/sms/login/',
    '/sms/send/'
]


NB_MENU = {
    'SUPERADMIN': [
        {
            'text': "用户信息",
            'icon': "fa-bed",
            'children': [
                {'text': "等级管理", 'url': "/level/list/", 'name': "level_list"},
                {'text': "客户管理", 'url': "/customer/list/", 'name': "customer_list"},
                {'text': "交易记录", 'url': "/policy/list/", 'name': "policy_list"},
            ]
        },

        {
            'text': "游戏订单管理",
            'icon': "fa-bed",
            'children': [
                {'text': "待支付游戏订单", 'url': "/gameorder/list/", 'name': "gameorder_list"},
                {'text': "已处理游戏订单", 'url': "/upload/list2/", 'name': "policy_list2"},
                {'text': "游戏名称", 'url': "/gamename/list/", 'name': "gamename_list"},
                {'text': "游戏面额", 'url': "/gamedenomination/list/", 'name': "gamedenomination_list"},
                # {'text': "城市列表", 'url': "/city/list/", 'name': "city_list"},
                # {'text': "城市列表2", 'url': "/city/list2/", 'name': "city_list"},
            ]
        },
    ],

    'ADMIN': [
        {
            'text': "用户信息",
            'icon': "fa-bed",
            'children': [
                {'text': "等级管理", 'url': "/level/list/", 'name': "level_list"},
                {'text': "客户管理", 'url': "/customer/list/", 'name': "customer_list"},
                {'text': "交易记录", 'url': "/policy/list/", 'name': "policy_list"},
            ]
        },

        {
            'text': "游戏订单管理",
            'icon': "fa-bed",
            'children': [
                {'text': "待支付游戏订单", 'url': "/gameorder/list/", 'name': "gameorder_list"},
                {'text': "已处理游戏订单", 'url': "/upload/list2/", 'name': "policy_list2"},
                {'text': "游戏名称", 'url': "/gamename/list/", 'name': "gamename_list"},
                {'text': "游戏面额", 'url': "/gamedenomination/list/", 'name': "gamedenomination_list"},
                # {'text': "城市列表", 'url': "/city/list/", 'name': "city_list"},
                # {'text': "城市列表2", 'url': "/city/list2/", 'name': "city_list"},
            ]
        },

        {
            'text': "话费订单管理",
            'icon': "fa-bed",
            'children': [
                {'text': "待支付话费订单", 'url': "/logging_module/pratice/", 'name': "logging_module_practice"},
                {'text': "已处理话费订单", 'url': "/logging_module/pratice/settings/", 'name': "logging_module_practice_settings"},
                # {'text': "价格策略", 'url': "/policy/list/", 'name': "policy_list"},
            ]
        },

    ],
    'CUSTOMER': [
        {
            'text': "订单中心",
            'icon': "fa-bed",
            'children': [
                {'text': "订单管理", 'url': "/my/order/list/", 'name': "my_order_list"},
                {'text': "我的交易记录", 'url': "/my/transaction/list/", 'name': "my_transaction_list"},
            ]
        },
    ],
}

PERMISSION_PUBLIC = {
    # "home": {"text": "主页", 'parent': None},

    "logout": {"text": "注销", 'parent': None},
    "media": {"text": "用户上传的媒体文件", 'parent': None},
    "client_info_view": {"text": "info", 'parent': None},
    # "sms_send": {"text": "发送短信", 'parent': None},
    "qbsearch": {"text": "info", 'parent': None},
    "gameorder_edit_log": {"text": "游戏订单编辑日志", 'parent': None},
}
PERMISSION = {
    "SUPERADMIN": {
"media": {"text": "用户上传的媒体文件", 'parent': None},
        "home": {"text": "主页", 'parent': None},
        'order_list':{'text':'订单展示','parent':'order'},
        'order_add':{'text':'创建订单','parent':'home'},

        "level_list": {"text": "级别列表", 'parent': None},
        "level_add": {"text": "新建级别", 'parent': 'level_list'},
        "level_edit": {"text": "编辑级别", 'parent': 'level_list'},
        "level_delete": {"text": "删除级别", 'parent': 'level_list'},

        "customer_list": {"text": "客户列表", 'parent': None},
        "customer_add": {"text": "添加客户", 'parent': 'customer_list'},
        "customer_edit": {"text": "编辑客户", 'parent': 'customer_list'},
        "customer_delete": {"text": "删除客户", 'parent': 'customer_list'},
        "customer_reset": {"text": "重置客户密码", 'parent': 'customer_list'},
        "customer_charge": {"text": "客户交易记录", 'parent': 'customer_list'},
        "customer_charge_add": {"text": "添加客户交易记录", 'parent': 'customer_list'},
        "customer_login_log": {"text": "客户登录记录", 'parent': 'customer_list'},


        "gameorder_list": {"text": "游戏订单", 'parent': None},
        "gameorder_add": {"text": "创建游戏订单", 'parent': 'gameorder_list'},
        "gameorder_edit": {"text": "编辑游戏订单", 'parent': 'gameorder_list'},
        "gameorder_delete": {"text": "删除游戏订单", 'parent': 'gameorder_list'},
        "gameorder_load_charge_options": {"text": "批量上传价格策略", 'parent': 'gameorder_list'},

        "gamename_list": {"text": "游戏名称列表", 'parent': None},
        "gamename_add": {"text": "添加游戏名称", 'parent': 'gamename_list'},
        "gamename_edit": {"text": "编辑游戏名称", 'parent': 'gamename_list'},
        "gamename_delete": {"text": "删除游戏名称", 'parent': 'gamename_list'},

        "gamedenomination_list": {"text": "游戏面额表", 'parent': None},
        "gamedenomination_add": {"text": "添加游戏面额", 'parent': 'gamedenomination_list'},
        "gamedenomination_edit": {"text": "编辑游戏面额", 'parent': 'gamedenomination_list'},
        "gamedenomination_delete": {"text": "删除游戏面额", 'parent': 'gamedenomination_list'},

        "upload_list": {"text": "上传文件", 'parent': None},
        "upload_list1": {"text": "上传文件1", 'parent': 'upload_list'},
        "upload_list2": {"text": "上传文件2", 'parent': 'upload_list'},
        "upload_list3": {"text": "上传文件3", 'parent': 'upload_list'},
        "upload_list4": {"text": "上传文件4", 'parent': 'upload_list'},
        "city_list": {"text": "城市列表", 'parent': 'upload_list'},
        "city_list2": {"text": "城市列表2", 'parent': 'upload_list'},

        "logging_module_practice":{"text":"日志模块练习","parent":None},
        "logging_module_practice_settings":{"text":"日志模块练习-配合settings","parent":'logging_module_practice'},
    },

    "ADMIN": {
        "home": {"text": "主页", 'parent': None},
        'order_list':{'text':'订单展示','parent':'order'},
        'order_add':{'text':'创建订单','parent':'home'},

        "level_list": {"text": "级别列表", 'parent': None},
        "level_add": {"text": "新建级别", 'parent': 'level_list'},
        "level_edit": {"text": "编辑级别", 'parent': 'level_list'},
        "level_delete": {"text": "删除级别", 'parent': 'level_list'},

        "customer_list": {"text": "客户列表", 'parent': None},
        "customer_add": {"text": "添加客户", 'parent': 'customer_list'},
        "customer_edit": {"text": "编辑客户", 'parent': 'customer_list'},
        "customer_delete": {"text": "删除客户", 'parent': 'customer_list'},
        "customer_reset": {"text": "重置客户密码", 'parent': 'customer_list'},
        "customer_charge": {"text": "客户交易记录", 'parent': 'customer_list'},
        "customer_charge_add": {"text": "添加客户交易记录", 'parent': 'customer_list'},
        "customer_login_log": {"text": "客户登录记录", 'parent': 'customer_list'},


        "gameorder_list": {"text": "游戏订单", 'parent': None},
        "gameorder_add": {"text": "创建游戏订单", 'parent': 'gameorder_list'},
        "gameorder_edit": {"text": "编辑游戏订单", 'parent': 'gameorder_list'},
        "gameorder_delete": {"text": "删除游戏订单", 'parent': 'gameorder_list'},
        "gameorder_load_charge_options": {"text": "批量上传价格策略", 'parent': 'gameorder_list'},

        "gamename_list": {"text": "游戏名称列表", 'parent': None},
        "gamedenomination_list": {"text": "游戏面额表", 'parent': None},

        "upload_list": {"text": "上传文件", 'parent': None},
        "upload_list1": {"text": "上传文件1", 'parent': 'upload_list'},
        "upload_list2": {"text": "上传文件2", 'parent': 'upload_list'},
        "upload_list3": {"text": "上传文件3", 'parent': 'upload_list'},
        "upload_list4": {"text": "上传文件4", 'parent': 'upload_list'},
        "city_list": {"text": "城市列表", 'parent': 'upload_list'},
        "city_list2": {"text": "城市列表2", 'parent': 'upload_list'},

        "logging_module_practice":{"text":"日志模块练习","parent":None},
        "logging_module_practice_settings":{"text":"日志模块练习-配合settings","parent":'logging_module_practice'},
    },
    "CUSTOMER": {
        "my_order_list": {"text": "订单列表", 'parent': None},
        "my_order_add": {"text": "订单列表", 'parent': 'my_order_list'},
        "my_order_cancel": {"text": "订单列表", 'parent': 'my_order_list'},
        "my_transaction_list": {"text": "订单列表", 'parent': None},

    }
}

QUEUE_TASK_NAME = "YANG_TASK_QUEUE"
# 使用cache存储
# MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'
# 或
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'
# 或使用fallback（默认）
# MESSAGE_STORAGE = 'django.contrib.messages.storage.fallback.FallbackStorage'


MESSAGE_DANGER_TAG = 50

MESSAGE_TAGS = {
    MESSAGE_DANGER_TAG:'danger',
}

T_SECRET_ID = '123'
T_SECRET_KEY = '123'





IPGEOLOCATION_API_KEY = 'b49f8dd322c746578d1c734ff1118b57'


# settings.py
# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': False,
#     'handlers': {
#         'console': {
#             'class': 'logging.StreamHandler',
#         },
#     },
#     'root': {
#         'handlers': ['console'],
#         'level': 'DEBUG',
#     },
# }

# settings.py
import colorlog
# 日志目录
LOG_DIR = BASE_DIR / 'logs'  # 在项目根目录下创建 logs 文件夹
# 如果日志目录不存在，则创建
if not LOG_DIR.exists():
    LOG_DIR.mkdir(parents=True, exist_ok=True)  # 确保目录存在
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,  # 不禁用现有记录器

    # 格式化器
    'formatters': {
        'standard': {
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'colored': {
            '()': 'colorlog.ColoredFormatter',  # 使用 colorlog 的 ColoredFormatter
            'format': '%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
            'log_colors': {
                'DEBUG': 'cyan',      # DEBUG 级别：青色
                'INFO': 'green',      # INFO 级别：绿色
                'WARNING': 'yellow',  # WARNING 级别：黄色
                'ERROR': 'red',       # ERROR 级别：红色
                'CRITICAL': 'red,bg_white',  # CRITICAL 级别：红色字体，白色背景
            },
        },
    },

    # 处理器
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'colored',  # 使用带颜色的格式化器
            'level': 'DEBUG',        # 控制台处理器记录 DEBUG 及以上级别的日志
        },
        'file_django': {  # Django 日志文件处理器
            'class': 'logging.FileHandler',
            'filename': LOG_DIR / 'django.log',  # 指定 Django 日志文件位置
            'formatter': 'standard',  # 使用标准格式化器
            'level': 'INFO',          # 记录 INFO 及以上级别的日志
        },
        'file_web': {  # web 模块日志文件处理器
            'class': 'logging.FileHandler',
            'filename': LOG_DIR / 'web.log',  # 指定 web 模块日志文件位置
            'formatter': 'standard',  # 使用标准格式化器
            'level': 'DEBUG',         # 记录 DEBUG 及以上级别的日志
        },
    },

    # 记录器
    'loggers': {
        'django': {
            'handlers': ['console', 'file_django'],  # Django 日志输出到控制台和文件
            'level': 'INFO',  # Django 记录 INFO 及以上级别的日志
            'propagate': False,  # 不传递给父记录器
        },
        'web': {
            'handlers': ['console', 'file_web'],  # web 模块日志输出到控制台和独立文件
            'level': 'DEBUG',  # web 模块记录 DEBUG 及以上级别的日志
            'propagate': False,  # 不传递给父记录器
        },
    },
}

import os
# 用于定义 用户上传文件（媒体文件）的本地存储路径
MEDIA_ROOT = os.path.join(BASE_DIR, "media")
print('BASE_DIR:',BASE_DIR)
MEDIA_URL = "/media/"


SYS_FEE = 1
THIRD_FEE = 0.5