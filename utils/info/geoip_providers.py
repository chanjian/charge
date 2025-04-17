import requests
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from django.conf import settings


import logging
logger = logging.getLogger(__name__)


class GeoIPService:
    PROVIDERS = [
        {
            'name': 'ipapi',
            'enabled': True,
            'method': '_query_ipapi',
            'timeout': 3,
            'priority': 1
        },
        {
            'name': 'ipgeolocation',
            'enabled': True,
            'method': '_query_ipgeolocation',
            'timeout': 5,
            'priority': 2,
            'api_key': getattr(settings, 'IPGEOLOCATION_API_KEY', None),
        }
    ]

    @classmethod
    def get_client_ip(cls, request):
        """获取客户端真实IP"""
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        print('xff',xff,type(xff))

        if xff:
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

    @classmethod
    def get_location(cls, ip):
        """获取最佳地理位置结果"""
        results = cls.get_all_providers_results(ip)
        for provider in sorted(cls.PROVIDERS, key=lambda x: x['priority']):
            if provider['enabled'] and provider['name'] in results:
                result = results[provider['name']]
                if 'error' not in result:
                    return result
        return {'error': 'All providers failed'}

    @classmethod
    def get_all_providers_results(cls, ip):
        """获取所有服务商的结果"""
        results = {}
        for provider in cls.PROVIDERS:
            if provider['enabled']:
                try:
                    method = getattr(cls, provider['method'])
                    results[provider['name']] = method(ip, provider.get('timeout', 3))
                except Exception as e:
                    results[provider['name']] = {'error': str(e)}
        return results

    @staticmethod
    def _query_ipapi(ip, timeout):
        """ipapi.co服务查询"""
        url = f"https://ipapi.co/{ip}/json/"
        try:
            resp = requests.get(url, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    'ip': ip,
                    'country': data.get('country_name'),
                    'region': data.get('region'),
                    'city': data.get('city'),
                    'latitude': data.get('latitude'),
                    'longitude': data.get('longitude'),
                    'isp': data.get('org'),
                }
            return {'error': f"HTTP {resp.status_code}"}
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def _query_ipgeolocation(ip, timeout):
        """ipgeolocation.io服务查询"""
        api_key = getattr(settings, 'IPGEOLOCATION_API_KEY', None)
        if not api_key:
            return {'error': 'API key not configured'}

        url = "https://api.ipgeolocation.io/ipgeo"
        params = {'apiKey': api_key, 'ip': ip}
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('message'):
                    return {'error': data['message']}

                # 生成百度地图链接
                lat = data.get('latitude')
                lng = data.get('longitude')
                map_url = f"https://map.baidu.com/?lat={lat}&lng={lng}" if lat and lng else None

                return {
                    'ip': ip,
                    'country': data.get('country_name'),
                    'region': data.get('state_prov'),
                    'city': data.get('city'),
                    'latitude': lat,
                    'longitude': lng,
                    'isp': data.get('isp'),
                    'map_url': map_url,
                    'exact_address': GeoIPService._get_exact_address(lat, lng),
                }
            return {'error': f"HTTP {resp.status_code}"}
        except Exception as e:
            return {'error': str(e)}

    @staticmethod
    def _get_exact_address(latitude, longitude):
        """使用geopy解析精确地址"""
        if not latitude or not longitude:
            return None

        try:
            geolocator = Nominatim(user_agent="geoapiExercises")
            location = geolocator.reverse(f"{latitude},{longitude}", language="zh", timeout=10)
            return location.address if location else None
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            logger.warning(f"Geocoding error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Geocoding failed: {str(e)}", exc_info=True)
            return None