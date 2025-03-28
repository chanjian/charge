from concurrent.futures import ThreadPoolExecutor


def geetest():
    try:
        # 实现滑动验证
        return True, 123
    except Exception as e:
        return False, str(e)


def send_sms():
    for i in range(5):
        try:
            # 发送短信
            return True, 123
        except Exception as e:
            pass

    return False, "短信发送异常了"


def login():
    while True:
        try:
            # 发送短信
            return True, 123
        except Exception as e:
            pass


def task(mobile, pwd):
    try:
        # 滑动验证
        status, data_or_error = geetest()
        if not status:
            # 错误记录， mobile+pwd+data_or_error + 滑动验证
            return

        # 发送短信
        status, data_or_error = send_sms()
        if not status:
            # 错误记录， mobile+pwd+data_or_error + 发送短信步骤
            return

        # 登录
        status, data_or_error = login()
        if not status:
            # 错误记录， mobile+pwd+data_or_error + 登录失败
            return

        func_list = [geetest, send_sms, login]
        for func in func_list:
            status, data = func()
            if not status:
                return



    except Exception as e:
        print("异常", e)  # 记录下来


def read_file():
    # 手机号,密码 500
    # 手机号,密码
    # 手机号,密码     v1,v2 = [11,22]
    with open('xxxx.txt', mode='r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            mobile, pwd = line.split(',')
            yield mobile, pwd


def run():
    pool = ThreadPoolExecutor(10)

    gen = read_file()
    for mobile, pwd in gen:
        # print(mobile, pwd)
        pool.submit(task, mobile, pwd)

    pool.shutdown()  # 主线程等待
    print("5000个任务全部执行完毕")


if __name__ == '__main__':
    run()
