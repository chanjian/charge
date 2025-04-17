# 修改后的 LoginInfoService 类
from utils.info.device_detector import DeviceDetector
from utils.info.geoip_providers import GeoIPService
from web.models import LoginLog, IPDetectionResult
import logging

logger = logging.getLogger(__name__)

class LoginInfoService:
    """登录信息服务，负责创建和处理登录记录"""

    @classmethod
    def create_login_record(cls, request, user):
        """
        创建基础登录记录并返回
        :param request: HttpRequest对象
        :param user: User对象,即登录用户对象
        :return: LoginLog对象
        """
        try:
            ip = cls._get_client_ip(request)
            login_log = LoginLog.objects.create(user=user, login_ip=ip)

            # Remove asynchronous task trigger, no longer calling delay here
            return login_log

        except Exception as e:
            logger.error(f"创建登录记录失败: {str(e)}", exc_info=True)
            raise

    @classmethod
    def process_login_info(cls, login_log_id, user_agent):
        """
        处理登录信息（由Celery任务调用）
        :param login_log_id: 登录记录ID
        :param user_agent: 用户代理字符串
        """
        print('6564545634634')
        try:
            login_log = LoginLog.objects.get(id=login_log_id)
            ip = login_log.login_ip

            device_info = cls._get_device_info(user_agent)
            print('device_info',device_info)
            geo_results = cls._get_geoip_results(ip)

            best_result = cls._save_detection_results(login_log, geo_results)
            if best_result:
                cls._update_login_log(login_log, best_result, device_info)

        except Exception as e:
            logger.error(f"处理登录信息失败: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def _get_client_ip(request):
        """获取客户端IP"""
        return GeoIPService.get_client_ip(request)

    @staticmethod
    def _get_device_info(user_agent):
        """获取设备信息"""
        return DeviceDetector.parse_user_agent(user_agent)

    @staticmethod
    def _get_geoip_results(ip):
        """获取所有IP检测结果"""
        return GeoIPService.get_all_providers_results(ip)

    @staticmethod
    def _save_detection_results(login_log, geo_results):
        """保存所有检测结果并返回最佳结果"""
        best_result = None
        for provider_name, result in geo_results.items():
            detection_result = IPDetectionResult.objects.create(
                login_log=login_log,
                provider_name=provider_name,
                is_valid='error' not in result,
                error_message=result.get('error'),
                raw_data=result,
                country=result.get('country'),
                region=result.get('region'),
                city=result.get('city'),
                latitude=result.get('latitude'),
                longitude=result.get('longitude'),
                isp=result.get('isp'),
                map_url=result.get('map_url'),
                exact_address=result.get('exact_address'),
            )

            if detection_result.is_valid and not best_result:
                best_result = detection_result
        return best_result

    @staticmethod
    def _update_login_log(login_log, detection_result, device_info):
        """更新登录日志主表"""
        login_log.login_city = detection_result.city
        login_log.login_province = detection_result.region
        login_log.login_device_type = device_info['device']['type']
        login_log.login_os = device_info['os']['family']
        login_log.login_browser = device_info['browser']['family']
        login_log.map_location = detection_result.map_url
        login_log.exact_address = detection_result.exact_address
        login_log.save()
