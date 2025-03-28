class LoginInfo:
    """客户端信息聚合容器"""

    def __init__(self):
        # 网络层信息
        self.network = NetworkInfo()

        # 设备层信息
        self.device = DeviceInfo()

        # 地理位置信息
        self.geo = GeoInfo()

        # 其他元数据
        self.fingerprint = None  # 设备指纹
        self.server_side = {}  # 服务器端补充信息


class NetworkInfo:
    """网络层信息"""

    def __init__(self):
        self.ip = None
        self.port = None
        self.protocol = None  # HTTP/HTTPS
        self.headers = {}  # 关键请求头
        self.proxy_chain = []  # 代理链 IP 列表


class DeviceInfo:
    """设备层信息"""

    def __init__(self):
        self.browser = BrowserInfo()
        self.os = OSInfo()
        self.device = HardwareInfo()
        self.screen = ScreenInfo()
        self.is_mobile = False
        self.is_tablet = False
        self.is_bot = False


class GeoInfo:
    """地理位置信息"""

    def __init__(self):
        self.country = None
        self.region = None
        self.city = None
        self.latitude = None
        self.longitude = None
        self.isp = None  # 网络服务提供商
        self.source = None  # 数据来源（如ip.sy）


class BrowserInfo:
    """浏览器信息"""

    def __init__(self):
        self.family = "Unknown"  # 浏览器名称（如 Chrome）
        self.version = (0, 0, 0)  # 浏览器版本号（元组）
        self.version_str = "0.0.0"  # 浏览器版本字符串


class OSInfo:
    """操作系统信息"""

    def __init__(self):
        self.family = "Unknown"  # 操作系统名称（如 Windows）
        self.version = (0, 0, 0)  # 操作系统版本号（元组）
        self.version_str = "0.0.0"  # 操作系统版本字符串


class HardwareInfo:
    """硬件设备信息"""

    def __init__(self):
        self.family = "Unknown"  # 设备类型（如 iPhone）
        self.brand = "Unknown"  # 设备品牌（如 Apple）
        self.model = "Unknown"  # 设备型号（如 iPhone 12）


class ScreenInfo:
    """屏幕信息"""

    def __init__(self):
        self.width = 0  # 屏幕宽度
        self.height = 0  # 屏幕高度
        self.color_depth = 24  # 颜色深度
        self.pixel_ratio = 1.0  # 设备像素比