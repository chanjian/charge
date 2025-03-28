from datetime import datetime
import os
import re
from django.conf import settings
from django.core.exceptions import SuspiciousFileOperation


def get_upload_path(file_object, username):
    """
    获取文件上传路径并确保目录存在
    格式: media/用户名/年份/月份/日/文件名

    修改点（保持原有username处理不变）：
    1. 优化目录创建逻辑
    2. 增加目录可写性验证
    3. 明确权限设置
    """
    # 1. 获取当前日期（保持不变）
    now = datetime.now()
    year = now.strftime('%Y')
    month = now.strftime('%m')
    day = now.strftime('%d')

    # 2. 处理文件名（保持不变）
    original_name = file_object.name
    base_name = os.path.basename(original_name)
    clean_name = re.sub(r'[^\w\-_.]', '_', base_name)

    if not clean_name:
        raise SuspiciousFileOperation("无效的文件名")

    # 3. 构建路径结构（保持不变）
    path_parts = [
        'media',  # 基础媒体目录
        username,  # 保持原始username不变 ← 明确不修改
        year,
        month,
        day,
        clean_name
    ]

    # 4. 生成相对路径（保持不变）
    relative_path = os.path.join(*path_parts)

    # === 修改点1：优化目录创建逻辑 ===
    # 计算需要创建的目录路径（排除文件名）
    dirs_to_create = os.path.join(settings.MEDIA_ROOT, username, year, month, day)

    try:
        # 创建目录（exist_ok=True避免竞态条件）
        os.makedirs(dirs_to_create, mode=0o755, exist_ok=True)  # ← 修改点2：明确设置权限

        # === 修改点3：验证目录可写性 ===
        test_file = os.path.join(dirs_to_create, '.tmp_permission_test')
        try:
            with open(test_file, 'w') as f:
                f.write('test')
            os.unlink(test_file)
        except IOError as e:
            raise OSError(f"目录不可写: {dirs_to_create} (请检查权限)")

    except OSError as e:
        raise OSError(f"无法创建目录: {dirs_to_create} (错误: {e})")

    # 5. 返回路径（保持不变）
    absolute_path = os.path.join(dirs_to_create, clean_name)
    print(f'[UPLOAD] 文件存储路径: {absolute_path}')  # ← 修改点4：更清晰的日志

    return relative_path, absolute_path