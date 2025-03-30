import requests
import time

# 记录开始时间
start_time = time.time()
# urls = ('http://headfirstlabs.com','http://oreilly.com','http://twitter.com')
urls = ('http://baidu.com','http://tencent.com','http://oneplus.com')


for resp in [requests.get(url) for url in urls]:
    print(len(resp.content),'->',resp.status_code,'->',resp.url)

# 计算并打印总耗时
end_time = time.time()
total_time = end_time - start_time
print(f"\n总运行时间: {total_time:.2f} 秒")


# import requests
# import time
#
# # 记录开始时间
# start_time = time.time()
#
# # urls = ('http://headfirstlabs.com','http://oreilly.com','http://twitter.com')
# urls = ('http://baidu.com','http://tencent.com','http://oneplus.com')
#
#
# for resp in (requests.get(url) for url in urls):
#     print(len(resp.content),'->',resp.status_code,'->',resp.url)
# # 计算并打印总耗时
# end_time = time.time()
# total_time = end_time - start_time
# print(f"\n总运行时间: {total_time:.2f} 秒")
