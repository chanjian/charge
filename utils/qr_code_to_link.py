from pyzbar import pyzbar
from PIL import Image

def qr_code_to_link(image_path):
    """
    解析二维码图像，返回二维码中的链接。

    :param image_path: 二维码图像的路径（字符串）
    :return: 二维码中的链接（字符串），如果未找到二维码则返回 None
    """
    try:
        # 打开图像
        image = Image.open(image_path)

        # 使用 pyzbar 解析二维码
        decoded_objects = pyzbar.decode(image)

        # 检查是否解析到二维码
        if not decoded_objects:
            print("未找到二维码")
            return None

        # 提取二维码数据
        for obj in decoded_objects:
            if obj.type == 'QRCODE':  # 确保是二维码
                qr_data = obj.data.decode('utf-8')  # 解码数据
                print("解析到的二维码数据:", qr_data)
                return qr_data

        print("未找到有效的二维码数据")
        return None

    except Exception as e:
        print("解析二维码时出错:", e)
        return None