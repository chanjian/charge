from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


print(Path(__file__))  #当前文件的绝对路径
print(Path(__file__).resolve())
print(Path(__file__).resolve().parent)
print(Path(__file__).resolve().parent.parent)
print('BASE_DIR:',BASE_DIR)


import os
print(os.path)