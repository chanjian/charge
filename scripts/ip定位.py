import requests


def get_ip_geolocation(api_key, ip_address=None):
    # API 端点
    url = "https://api.ipgeolocation.io/ipgeo"

    # 请求参数
    params = {
        "apiKey": 'b49f8dd322c746578d1c734ff1118b57',
        "ip": '36.33.36.221'  # 如果不提供 IP 地址，API 会返回当前请求的 IP 地址信息
    }

    # 发送 GET 请求
    response = requests.get(url, params=params)

    # 检查请求是否成功
    if response.status_code == 200:
        return response.json()  # 返回 JSON 格式的地理位置信息
    else:
        return f"Error: {response.status_code}, {response.text}"


# 你的 API 密钥
api_key = "b49f8dd322c746578d1c734ff1118b57"

# 要查询的 IP 地址（可选，如果不提供则查询当前 IP）
ip_address = "36.33.36.221"  # 例如：Google 的公共 DNS IP

# 获取地理位置信息
geolocation_data = get_ip_geolocation(api_key, ip_address)

# 打印结果
print(geolocation_data)