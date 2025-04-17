################使用time模块################
print('################以下是使用time模块################')
import time

# 获取当前时间戳（从 1970 年 1 月 1 日 00:00:00 UTC 到现在的秒数）
timestamp = time.time()
print(f"当前时间戳: {timestamp}")

# 将时间戳转换为本地时间的 struct_time 对象
local_time = time.localtime(timestamp)
print(local_time)

# 格式化输出本地时间
formatted_time = time.strftime("%Y-%m-%d %H:%M:%S", local_time)
print(f"格式化后的本地时间: {formatted_time}")

##################以下是datetime模块##################
print('##################以下是datetime模块##################')
import datetime
now = datetime.datetime.now()
print(now)
print(now.time())

###################以下是Django框架独有的timezone#####################
print('###################以下是Django框架独有的timezone#####################')
from django.utils import timezone
from SemiAutomaticChargeSystem import settings
# 获取当前 UTC 时间
utc_now = timezone.now()
print(f"当前 UTC 时间: {utc_now}")

# 将 UTC 时间转换为本地时区时间
local_now = timezone.localtime(utc_now)
print(f"当前本地时区时间: {local_now}")

######################################
print('##################以下是使用arrow模块####################')
import arrow

# 获取当前的日期和时间，返回一个 Arrow 对象
now = arrow.now()
print(f"当前的日期和时间: {now}")

# 格式化输出当前时间，支持多种格式化字符串
formatted_now = now.format('YYYY-MM-DD HH:mm:ss')
print(f"格式化后的日期和时间: {formatted_now}")
