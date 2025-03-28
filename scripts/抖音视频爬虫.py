# 利用DrissionPage爬取抖音视频, 抖音需要JS逆向，直接用DP不需要逆向
# 直接抓包后分析B站的网络发现没有JS逆向，直接爬取
# LeoTT 2025/01/26 video_download.py

# tk相关导入包
import re
import time
import threading
import tkinter as tk
from qrcode import QRCode
from PIL import Image, ImageTk
from tkinter.messagebox import showinfo
# 爬虫相关导入包
import os
import json
import ffmpeg
import requests
from lxml import etree
from DrissionPage import ChromiumPage
from DrissionPage import ChromiumOptions

# =================以下是抖音/B站爬虫=================
# =================以下是抖音/B站爬虫=================
cp = ChromiumOptions()
cp.headless(True)  # 设置无头浏览器
bilibili_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36',
    'Referer': 'https://www.bilibili.com',
    'Origin': 'https://www.bilibili.com'}


def readCookie(cookie_path):
    try:
        with open(cookie_path, 'r', encoding='utf-8') as f:
            cookies = f.readline()
            if not cookies.strip():  # 使用 strip() 去除可能的前后空白字符，然后检查是否为空
                raise ValueError(f"The file {cookie_path} is empty.")
            return eval(cookies)
    except FileNotFoundError:
        return
        print("文件不存在")


def video_download_com():
    exec_path, video_type = extract_share_path()
    if exec_path == 'error':
        return
    save_path_all = save_path.get()
    if save_path_all == '请输入保存路径,不输入默认同级保存!':
        save_path_all = None

    if video_type == 'douyin':
        try:
            chrome = ChromiumPage(cp)
        except:
            showinfo("警告", "本电脑未安装谷歌浏览器!该软件无法正常运行!请安装谷歌浏览器后再次试运行!")
            return
        chrome.listen.start('douyin.com/aweme/v1/web/aweme/detail/')
        chrome.get(exec_path)
        for packet in chrome.listen.steps():
            detail_body = packet.response.body
            aweme_detail = detail_body.get('aweme_detail')
            desc = aweme_detail.get('desc')
            video = aweme_detail.get('video')
            bit_rate = video.get('bit_rate')
            # bit_rate是一个视频列表，有不同分辨率的视频，按观察第0个最清晰
            if bit_rate:
                video = bit_rate[0]
                play_addr = video.get('play_addr')
                url_list = play_addr.get('url_list')
                if len(url_list) == 3:
                    url_download = url_list[2]
                    download_by_request(url_download, packet.response.headers, desc, save_path_all)
                    break
                else:
                    continue
        chrome.quit()
    if video_type == 'bilibili':
        # 从C盘读取B站cookies
        cookies = readCookie('bilibili_cookies.txt')
        # 分别获取视频和音频两个链接，B站没有反扒机制，可以直接拿
        r = requests.get(exec_path, headers=bilibili_headers, cookies=cookies) if cookies else requests.get(exec_path,
                                                                                                            headers=bilibili_headers)
        info = re.findall('window.__playinfo__=(.*?)</script>', r.text)[0]
        video_url = json.loads(info)["data"]["dash"]["video"][0]["baseUrl"]
        audio_url = json.loads(info)["data"]["dash"]["audio"][0]["baseUrl"]
        html = etree.HTML(r.text)
        filename = html.xpath('//h1/text()')[0]
        # 视频名称可能有非法字符，无法正常创建，删掉非法字符
        illegal_chars = '<>:\"/\\|?*'
        for char in illegal_chars:
            filename = filename.replace(char, '')

        # 下载音频和视频，返回的是字节，ffmpeg处理的是流，策略一：使用临时文件；策略二：使用BytesIO+管道
        video_content = requests.get(video_url, headers=bilibili_headers).content
        audio_content = requests.get(audio_url, headers=bilibili_headers).content
        with open('temp.mp4', 'wb') as f:
            f.write(video_content)
            print("视频部分下载完毕")
        with open('temp.mp3', 'wb') as f:
            f.write(audio_content)
            print("音频部分下载完毕")

        # 合并音视
        output_video = f'{save_path_all}/{filename}.mp4' if save_path_all else f'{filename}.mp4'
        audio_stream = ffmpeg.input('temp.mp3')
        video_stream = ffmpeg.input('temp.mp4')
        output_stream = ffmpeg.output(audio_stream, video_stream, output_video, vcodec='copy', acodec='aac')
        ffmpeg.run(output_stream)
        os.remove('temp.mp4')
        os.remove('temp.mp3')
        showinfo("恭喜", "视频已下载！")


def download_by_request(url, headers, file_name, save_path):
    # FixBug：DrissionPage的download跟downloadKit模块一直报错403跟404，不知道是调用方法有问题还是怎么，自己写一个
    # 抖音上的视频名称有非法字符，无法正常创建，删掉非法字符
    illegal_chars = '<>:\"/\\|?*'
    for char in illegal_chars:
        file_name = file_name.replace(char, '')

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        video_save_path = save_path + '\\' + file_name + '.mp4' if save_path else file_name + '.mp4'
        try:
            with open(video_save_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            showinfo("恭喜", "视频已下载！")
        except Exception as e:
            raise Exception("警告", "视频解析已成功，但是在保存下载视频时遇到其他问题！" + e)


# ==============以下是tkinter的操作===============
# ==============以下是tkinter的操作===============
def extract_share_path():
    share_path_all = share_path.get()
    if not share_path_all:
        showinfo("警告", "分享链接为空！请点击分享后将分享口令粘贴到【分享链接】！")
        return

    pattern = r'https://v.douyin.com/[@a-zA-Z0-9-_]+/'
    match = re.search(pattern, share_path_all)
    if match:
        share_path.delete(0, tk.END)  # 清空之前的内容
        share_path.insert(0, match.group())  # 插入新的文件路径
        return match.group(), 'douyin'

    bili_pattern = r'https://www.bilibili.com/video/[@a-zA-Z0-9-_]+/'
    match = re.search(bili_pattern, share_path_all)
    if match:
        share_path.delete(0, tk.END)  # 清空之前的内容
        share_path.insert(0, match.group())  # 插入新的文件路径
        return match.group(), 'bilibili'

    showinfo("警告",
             "未发现分享链接！链接应形如【https://v.douyin.com/xxxxxxxx/】或【https://www.bilibili.com/video/xxxxxxxx/】")
    return 'error', 'error'


def on_share_path_click(event):
    if share_path.get() == '将B站/抖音分享的口令粘贴到此处!':  # 如果输入框为默认文本，则清除它
        share_path.delete(0, tk.END)
    share_path.icursor(0)  # 将光标移动到输入框的开头


def on_share_path_focus_out(event):
    if share_path.get() == '':  # 如果输入框为空，则插入默认文本
        share_path.insert(0, '将B站/抖音分享的口令粘贴到此处!')


def on_save_path_click(event):
    if save_path.get() == '请输入保存路径,不输入默认同级保存!':
        save_path.delete(0, tk.END)
    save_path.icursor(0)


def on_save_path_focus_out(event):
    if save_path.get() == '':
        save_path.insert(0, '请输入保存路径,不输入默认同级保存!')


def on_login_click():
    global new_window
    new_window = tk.Toplevel(root)
    new_window.geometry("300x210")
    new_window.title("B站扫码登录")

    # 下面这段代码将登录链接转成二维码然后贴在tkinter新界面上
    url = 'https://passport.bilibili.com/x/passport-login/web/qrcode/generate?source=main-fe-header'
    response = requests.get(url=url, headers=bilibili_headers).json()
    qrcode_key = response['data']['qrcode_key']
    label = tk.Label(new_window)
    # 创建二维码对象
    qr = QRCode()
    # 设置二维码的数据
    qr.add_data(response['data']['url'])
    # 生成二维码图片
    img = qr.make_image()
    img = img.resize((200, 200), resample=Image.BICUBIC)
    # 使用PIL的ImageTK将PIL图像转为TKinter可以使用的格式
    photo = ImageTk.PhotoImage(img)
    # 更新标签中的图像
    label.config(image=photo)
    label.image = photo  # 保持对图像的引用，防止被垃圾回收
    label.pack()

    # 检测线程，检测是否已经扫码
    thread = threading.Thread(target=check_login, args=(qrcode_key,))
    thread.start()


def check_login(qrcode_key):
    global new_window
    # 循环检测是否已经扫码
    check_login_url = f'https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key={qrcode_key}&source=main-fe-header'
    session = requests.Session()
    while True:
        data = session.get(url=check_login_url, headers=bilibili_headers).json()
        if data['data']['code'] == 0:
            # 使用Session发起请求
            response = session.get('https://www.bilibili.com/', headers=bilibili_headers)
            # 保存cookies
            with open('bilibili_cookies.txt', 'w') as f:
                f.write(str(session.cookies.get_dict()))
                print('cookies保存成功')
            check_cookies()
            break
        if not new_window.winfo_exists():
            # 扫码窗口已经被主动关闭了，退出线程
            break
        time.sleep(1)
    if new_window:
        new_window.destroy()


def check_cookies():
    try:
        with open('bilibili_cookies.txt', 'r', encoding='utf-8') as f:
            cookies = f.readline()
            if not cookies.strip():  # 使用 strip() 去除可能的前后空白字符，然后检查是否为空
                print("没有cookies")
                return
    except FileNotFoundError:
        print("文件不存在")
        return
    cookies = eval(cookies)
    # 发送HTTP请求获取登录状态信息
    login_url = requests.get("https://api.bilibili.com/x/web-interface/nav", headers=bilibili_headers,
                             cookies=cookies).json()
    # 判断登录状态
    if login_url['code'] == 0:
        # 如果登录状态码为0，则表示登录成功
        print(f"Cookies值有效, {login_url['data']['uname']}, 已登录！")
        global button_login
        button_login["text"] = login_url['data']['uname']
    else:
        # 如果登录状态码不为0，则表示登录失败
        print('Cookies值已经失效，请重新扫码登录！')


# ==============以下是界面布局===============
# ==============以下是界面布局===============
root = tk.Tk()
new_window = None
root.geometry("500x100")
root.title("无水印下载")
# -----文字、按钮、输入框等-----
share_path_name = tk.Label(root, text="分享链接：")
save_path_name = tk.Label(root, text="保存位置：")
share_path = tk.Entry(root, width=55)
save_path = tk.Entry(root, width=55)
button_login = tk.Button(root, text="扫描登录", cursor="hand2", bd=0, highlightthickness=0, overrelief="flat",
                         relief="flat", font=('Arial', 10), fg="blue", activeforeground="red", command=on_login_click)
LeoTT_name = tk.Label(root, text="--LeoTT开发免费分享")
button_download = tk.Button(root, text="解析下载", command=video_download_com)
# -----绑定默认提示语-----
share_path.insert(0, '将B站/抖音分享的口令粘贴到此处!')
save_path.insert(0, '请输入保存路径,不输入默认同级保存!')
share_path.bind('<FocusIn>', on_share_path_click)  # 绑定点击事件
share_path.bind('<FocusOut>', on_share_path_focus_out)  # 绑定失去焦点事件
save_path.bind('<FocusIn>', on_save_path_click)  # 绑定点击事件
save_path.bind('<FocusOut>', on_save_path_focus_out)  # 绑定失去焦点事件
# -----布局排布-----
share_path_name.place(x=15, y=10)
share_path.place(x=80, y=10)
save_path_name.place(x=15, y=35)
save_path.place(x=80, y=35)
button_login.place(x=15, y=70)
LeoTT_name.place(x=285, y=70)
button_download.place(x=410, y=65)
# -----主程序运行入口-----
check_cookies()
root.mainloop()
