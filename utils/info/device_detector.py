
from user_agents import parse
import json
import logging

logger = logging.getLogger(__name__)
class DeviceDetector:
    @staticmethod
    def get_advanced_device_info(request):
        """获取设备信息"""
        ua_string = request.META.get('HTTP_USER_AGENT', '')
        user_agent = parse(ua_string)

        # 基础设备信息
        device_info = {
            'browser': {
                'family': user_agent.browser.family,
                'version': tuple(user_agent.browser.version),
                'version_str': user_agent.browser.version_string,
            },
            'os': {
                'family': user_agent.os.family,
                'version': tuple(user_agent.os.version),
                'version_str': user_agent.os.version_string,
            },
            'device': {
                'family': user_agent.device.family,
                'brand': user_agent.device.brand,
                'model': user_agent.device.model,
            },
            'is_mobile': user_agent.is_mobile,
            'is_tablet': user_agent.is_tablet,
            'is_pc': user_agent.is_pc,
            'is_touch_capable': user_agent.is_touch_capable,
            'is_bot': user_agent.is_bot,
            'ua_string': ua_string,
        }

        # 判断设备类型
        if device_info['is_mobile']:
            device_type = "Mobile"
        elif device_info['is_tablet']:
            device_type = "Tablet"
        elif device_info['is_pc']:
            device_type = "PC"
        else:
            device_type = "Unknown"

        # 将设备类型添加到 device_info 中
        device_info['device']['type'] = device_type

        # 添加客户端屏幕信息
        DeviceDetector._parse_screen_info(request, device_info)

        return device_info

    @staticmethod
    def _parse_screen_info(request, device_info):
        """解析客户端屏幕信息"""
        if request.headers.get('X-Client-Screen'):
            try:
                screen_data = json.loads(request.headers['X-Client-Screen'])
                device_info['screen'] = {
                    'width': screen_data.get('w'),
                    'height': screen_data.get('h'),
                    'color_depth': screen_data.get('cd'),
                    'pixel_ratio': screen_data.get('pr'),
                }
            except Exception as e:
                logger.error(f"Failed to parse screen info: {str(e)}", exc_info=True)
