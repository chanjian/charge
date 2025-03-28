import requests
import logging

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from django.conf import settings  # 从 Django 的 settings 中获取配置

logger = logging.getLogger(__name__)


# class GeoIPService:
#     @classmethod
#     def get_location(cls, ip):
#         """
#         获取 IP 地址的地理位置信息
#         :param ip: 要查询的 IP 地址
#         :return: 包含多个服务商查询结果的字典
#         """
#         # 多服务商查询
#         providers = [
#             {"name": "ipapi", "method": cls._query_ipapi},
#             # 如果需要其他服务商，可以在这里添加
#             {"name": "ipgeolocation", "method": cls._query_ipgeolocation},
#         ]
#
#         results = {}  # 存储所有服务商的结果
#         for provider in providers:
#             # 调用服务商查询方法
#             result = provider["method"](ip)
#             if result:
#                 results[provider["name"]] = result
#             else:
#                 # 如果查询失败，记录错误信息
#                 results[provider["name"]] = {
#                     "source": provider["name"],
#                     "error": "No data returned from provider"
#                 }
#
#         # 返回所有服务商的结果
#         return results
#
#     @staticmethod
#     def _query_ipapi(ip):
#         """使用 ipapi.co 服务查询地理位置"""
#         try:
#             url = f"https://ipapi.co/{ip}/json/"
#             response = requests.get(url, timeout=3)
#             if response.status_code == 200:
#                 data = response.json()
#                 return {
#                     'source': 'ipapi',
#                     'country': data.get('country_name'),
#                     'region': data.get('region'),
#                     'city': data.get('city'),
#                     'latitude': data.get('latitude'),
#                     'longitude': data.get('longitude'),
#                     'asn': data.get('asn'),
#                     'isp': data.get('org'),
#                     'timezone': data.get('timezone'),
#                 }
#             else:
#                 return {
#                     'source': 'ipapi',
#                     'error': f"Request failed with status code {response.status_code}"
#                 }
#         except Exception as e:
#             return {
#                 'source': 'ipapi',
#                 'error': f"Exception occurred: {str(e)}"
#             }
#
#
#
#
#     @staticmethod
#     def _query_ipgeolocation(ip):
#         """使用 ipgeolocation.io 服务查询地理位置"""
#         try:
#             url = "https://api.ipgeolocation.io/ipgeo"
#             params = {
#                 "apiKey": settings.IPGEOLOCATION_API_KEY,  # 从 settings 中获取 API 密钥
#                 "ip": ip
#             }
#             response = requests.get(url, params=params, timeout=5)
#
#             # 处理 API 响应
#             if response.status_code == 200:
#                 data = response.json()
#
#                 # 检查 API 返回的错误信息
#                 if data.get("message"):
#                     return {
#                         'source': 'ipgeolocation',
#                         'error': f"API error: {data.get('message')}"
#                     }
#
#                 # 生成百度地图链接
#                 latitude = data.get('latitude')
#                 longitude = data.get('longitude')
#                 baidu_map_url = f"https://api.map.baidu.com/marker?location={latitude},{longitude}&title=定位地址&output=html"
#
#                 # 使用 geopy 解析精确地址
#                 exact_address = GeoIPService._get_exact_address(latitude, longitude)
#
#                 return {
#                     'source': 'ipgeolocation',
#                     'ip': data.get('ip'),
#                     'country': data.get('country_name'),
#                     'region': data.get('state_prov'),
#                     'city': data.get('city'),
#                     'latitude': latitude,
#                     'longitude': longitude,
#                     'asn': data.get('asn'),
#                     'isp': data.get('isp'),
#                     'timezone': data.get('time_zone', {}).get('name'),
#                     'baidu_map_url': baidu_map_url,  # 百度地图链接
#                     'exact_address': exact_address,  # 精确地址
#                 }
#             elif response.status_code == 403:
#                 return {
#                     'source': 'ipgeolocation',
#                     'error': "API key is invalid or quota exceeded"
#                 }
#             else:
#                 return {
#                     'source': 'ipgeolocation',
#                     'error': f"Request failed with status code {response.status_code}"
#                 }
#         except requests.exceptions.RequestException as e:
#             return {
#                 'source': 'ipgeolocation',
#                 'error': f"Request exception occurred: {str(e)}"
#             }
#         except Exception as e:
#             return {
#                 'source': 'ipgeolocation',
#                 'error': f"Unexpected exception occurred: {str(e)}"
#             }
#
#     @staticmethod
#     def _get_exact_address(latitude, longitude):
#         """使用 geopy 解析精确地址"""
#         try:
#             geolocator = Nominatim(user_agent="geoapiExercises")
#             location = geolocator.reverse(f"{latitude}, {longitude}", language="zh", timeout=10)
#             return location.address if location else "未知地址"
#         except GeocoderTimedOut:
#             return "地址解析超时"
#         except GeocoderServiceError:
#             return "地址解析服务不可用"
#         except Exception as e:
#             return f"地址解析失败: {str(e)}"
#
#     @staticmethod
#     def get_location(request):
#         """
#         获取 IP 地址的地理位置信息
#         :param request: Django 的 request 对象
#         :return: 包含查询结果的字典
#         """
#         # 从 request 中获取客户端 IP
#         ip = GeoIPService.get_client_ip(request)
#         if not ip:
#             return {
#                 'source': 'ipgeolocation',
#                 'error': "Failed to get client IP"
#             }
#
#         # 调用 IP 定位服务
#         return GeoIPService._query_ipgeolocation(ip)
#
#     @staticmethod
#     def get_client_ip(request):
#         """多层级获取真实 IP"""
#         x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
#         if x_forwarded_for:
#             ips = [ip.strip() for ip in x_forwarded_for.split(',')]
#             for ip in ips:
#                 if ip and ip != 'unknown':
#                     return ip.split(':')[0]  # 处理带端口的情况
#         return request.META.get('REMOTE_ADDR', '').split(':')[0]
#
#
#
#     @staticmethod
#     def get_client_ip(request):
#         """多层级获取真实IP"""
#         x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
#         if x_forwarded_for:
#             ips = [ip.strip() for ip in x_forwarded_for.split(',')]
#             for ip in ips:
#                 if ip and ip != 'unknown':
#                     # 返回第一个有效的ip
#                     return ip.split(':')[0]  # 处理带端口的情况
#                     # REMOTE_ADDR：如果 X-Forwarded-For 头不存在或没有有效的 IP 地址，则回退到 REMOTE_ADDR，这是 Django 默认的客户端 IP 地址。
#                     # split(':')[0]：同样处理可能包含端口的情况。
#                     # ''：如果 REMOTE_ADDR 也不存在，则返回空字符串。
#         return request.META.get('REMOTE_ADDR', '').split(':')[0]


class GeoIPService:
    @staticmethod
    def get_client_ip(request):
        """
        从请求中获取客户端 IP 地址
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]  # 获取第一个 IP
        else:
            ip = request.META.get('REMOTE_ADDR')  # 直接获取 IP
        return ip

    @staticmethod
    def get_location(request):
        """
        获取客户端的地理位置信息
        """
        ip = GeoIPService.get_client_ip(request)  # 获取客户端 IP
        if not ip:
            return {'error': '无法获取客户端 IP 地址'}

        # 调用 IP 地理位置服务
        return GeoIPService._query_ipgeolocation(ip)

    @staticmethod
    def _query_ipgeolocation(ip):
        """
        使用 ipgeolocation.io 服务查询地理位置
        """
        try:
            url = "https://api.ipgeolocation.io/ipgeo"
            params = {
                "apiKey": settings.IPGEOLOCATION_API_KEY,  # 从 settings 中获取 API 密钥
                "ip": ip
            }
            response = requests.get(url, params=params, timeout=5)

            # 处理 API 响应
            if response.status_code == 200:
                data = response.json()

                # 检查 API 返回的错误信息
                if data.get("message"):
                    return {
                        'source': 'ipgeolocation',
                        'error': f"API error: {data.get('message')}"
                    }

                # 生成百度地图链接
                latitude = data.get('latitude')
                longitude = data.get('longitude')
                baidu_map_url = f"https://api.map.baidu.com/marker?location={latitude},{longitude}&title=定位地址&output=html"

                # 使用 geopy 解析精确地址
                exact_address = GeoIPService._get_exact_address(latitude, longitude)

                return {
                    'source': 'ipgeolocation',
                    'ip': data.get('ip'),
                    'country': data.get('country_name'),
                    'region': data.get('state_prov'),
                    'city': data.get('city'),
                    'latitude': latitude,
                    'longitude': longitude,
                    'asn': data.get('asn'),
                    'isp': data.get('isp'),
                    'timezone': data.get('time_zone', {}).get('name'),
                    'baidu_map_url': baidu_map_url,  # 百度地图链接
                    'exact_address': exact_address,  # 精确地址
                }
            elif response.status_code == 403:
                return {
                    'source': 'ipgeolocation',
                    'error': "API key is invalid or quota exceeded"
                }
            else:
                return {
                    'source': 'ipgeolocation',
                    'error': f"Request failed with status code {response.status_code}"
                }
        except requests.exceptions.RequestException as e:
            return {
                'source': 'ipgeolocation',
                'error': f"Request exception occurred: {str(e)}"
            }
        except Exception as e:
            return {
                'source': 'ipgeolocation',
                'error': f"Unexpected exception occurred: {str(e)}"
            }

    @staticmethod
    def _get_exact_address(latitude, longitude):
        """
        使用 geopy 解析精确地址
        """
        try:
            geolocator = Nominatim(user_agent="geoapiExercises")
            location = geolocator.reverse(f"{latitude}, {longitude}", language="zh", timeout=10)
            return location.address if location else "未知地址"
        except GeocoderTimedOut:
            return "地址解析超时"
        except GeocoderServiceError:
            return "地址解析服务不可用"
        except Exception as e:
            return f"地址解析失败: {str(e)}"

