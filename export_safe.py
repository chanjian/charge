# export_safe.py
import os
import sys
import django
from django.core.management import call_command

def main():
    # 设置 Django 环境
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'SemiAutomaticChargeSystem.settings')
    django.setup()

    # 备份原始标准输出
    original_stdout = sys.stdout

    try:
        # 导出数据到文件
        with open('datadump_safe.json', 'w', encoding='utf-8') as f:
            sys.stdout = f  # 重定向标准输出
            call_command(
                'dumpdata',
                exclude=['contenttypes', 'auth.Permission', 'sessions'],
                indent=2,
                format='json',
                use_natural_foreign_keys=True
            )
    finally:
        # 确保总是恢复标准输出
        sys.stdout = original_stdout

    # 现在可以安全打印消息
    print("数据导出完成！文件保存为 datadump_safe.json")

if __name__ == '__main__':
    main()