import os


def get_directory_structure():
    # 获取当前所在目录
    current_directory = os.getcwd()
    print(f"当前所在目录: {current_directory}")

    directory_structure = {}
    # 遍历当前目录
    for root, dirs, files in os.walk(current_directory):
        # 计算当前目录相对于起始目录的层级
        level = root.replace(current_directory, '').count(os.sep)
        # 只处理到二级目录
        if level <= 2:
            # 从当前目录路径中提取出相对于起始目录的路径
            relative_path = os.path.relpath(root, current_directory)
            if relative_path == '.':
                relative_path = ''
            # 存储目录结构
            directory_structure[relative_path] = {
                'directories': dirs,
                'files': files
            }

    return directory_structure


if __name__ == "__main__":
    structure = get_directory_structure()
    for path, info in structure.items():
        if path:
            print(f"目录: {path}")
        else:
            print("当前目录")
        print("  子目录:")
        for dir_name in info['directories']:
            print(f"    {dir_name}")
        print("  文件:")

    