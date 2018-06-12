import requests
import os,os.path
import re
import random
import threading

from user_agent import generate_user_agent #生成随机User-Agent
from bs4 import BeautifulSoup as bs
from time import time,sleep
from queue import Queue


host = "http://1024.917rbb.biz/pw/"  # 用于拼接合集完整链接

merge_dict = {} # 用于保存一个合集的信息   {"合集名字":"合集的链接"}
torrent_url_queue = Queue()     # 用于储存可以直接用来下载的种子链接
user_agent = generate_user_agent()


# 验证码要提交到的链接
pic_check_url = "http://1024.917rbb.biz/cdn-cgi/l/chk_captcha"
# 验证码 提交时的参数
pic_params = {
    "id":"这里是js生成的id",
    "captcha_challenge_field":"这里是js生成的数据",
    "manual_captcha_challenge_field":"这里是验证码"
}
# 代理 https
proxies = ["119.10.67.144:808","106.8.17.31:60443","221.228.17.172:8181","114.99.4.233:808","120.78.78.141:8888","119.10.67.144:808"]
proxies_https = {"https":random.choice(proxies)}
# 网站请求头
headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Cookie":"__cfduid=d5b3c596dd9c7e5865e2faf6e4ac002041527325237; UM_distinctid=1639bad6331381-015d16c4c9c1d5-3c3c5b0b-1fa400-1639bad6333b89; aafaf_threadlog=%2C7%2C22%2C90%2C78%2C3%2C; cf_clearance=b2ab6daa649fa58357a0487f9f887a0d6ba69a46-1528697091-1800; aafaf_lastpos=index; aafaf_lastvisit=369%091528697740%09%2Fpw%2Findex.php%3F; aafaf_ol_offset=28712; CNZZDATA1261158850=2012564272-1528526470-null%7C1528693063",
    "Host":"1024.917rbb.biz",
    "Referer": "http://1024.917rbb.biz/pw/",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent":user_agent,
    }
# 网站cookies
cookies = {
    "astupdate":"1528609297",
    "__cfduid":"d5b3c596dd9c7e5865e2faf6e4ac002041527325237",
    "UM_distinctid":"1639bad6331381-015d16c4c9c1d5-3c3c5b0b-1fa400-1639bad6333b89",
    "aafaf_ol_offset":"449110",
    "CNZZDATA1261158850":"2012564272-1528526470-null%7C1528627064",
    "aafaf_threadlog":"%2C7%2C22%2C90%2C78%2C3%2C",
    "cf_clearance":"b2ab6daa649fa58357a0487f9f887a0d6ba69a46-1528697091-1800",
    "aafaf_lastpos":"index",
    "aafaf_lastvisit":"213%091528618622%09%2Fpw%2Findex.php%3F"
}

s = requests.session()

# 从首页获取分类信息,{"类名":"链接地址"}
# 这里只获取第一行的6个分类
def get_type_infos(index_url):
    try:
        response = s.get(index_url, headers=headers,cookies=cookies,proxies=proxies_https)

        if response.status_code > 200:
            print("网页无法加载！错误码：", response.status_code)
        else:
            response.encoding = "utf-8"  # 设置编码，防止乱码
            html = bs(response.text, 'lxml')
            print("成功进入网页：", html.title.string)
            a_type_list = html.select('#cate_1 tr.tr3 a')  # 返回所有分类信息，包含一些无用的
            type_1 = a_type_list[2:7]
            for each in type_1:
                type_dict[each.string] = host + each["href"]
                #print(each.string + "：", host + each["href"])
    except Exception as e:    # 换 IP重试
        t = int(input("IP 出现问题，是否重试：1:True  2:False"))
        if t == 1 or t == True:
            get_type_infos(index_url)

''' ---------------------------获取所需要的信息-------------------------------- '''
# 获取一个分类下的合集
def get_merge_info(type_url):
    #try:
        response = s.get(type_url,headers=headers)
        response.encoding="utf-8"
        if response.status_code == 403:     # 出现验证码
            print("检测到需要输入验证码，请稍后...")
            response = Captcha(s,type_url).captcha()
        print(response.text)
        html = bs(response.text, "lxml")
        print(html.text)
        normal_theme = html.find_all("tr",attrs={"class":"tr2"})[1] # 找到普通主题，用于定位下面的tr

        files_list = normal_theme.find_next_siblings("tr")[:-1] # 需要从里面筛选掉广告链接
        print("本页共 %d 个合集（含多个广告项）~"%len(files_list))

        # 通过遍历找到具体文件链接
        for each in files_list:
            """ 筛选掉广告链接"""
            if each.has_attr("onmouseover") or each.has_attr("onmouseout"):
                print("筛选广告项...")
            else:
                merge_name = each.select_one("h3 > a").string
                merge_url = host+each.select_one("h3 > a")["href"]
                merge_dict[merge_name] = merge_url
                #print(merge_name,merge_url)
    # except Exception:
    #     t = input("IP 出现问题，是否重试：1:True  2:False\n")
    #     if t == "1":
    #         get_merge_info(type_url)

# 获取一个集合下所有的torrent文件链接 加入下载队列,队列中元素形式   {"合集名字":"链接地址"}
# 睡 5 秒切换集合
def parse_all_torrent_url():
    """make a folder with the merge_name,download the torrent file into it meanwhile"""
    try:
        for merge_name, merge_url in merge_dict.items():
            response = s.get(merge_url)
            response.encoding = "utf-8"
            sleep(1)
            if response.status_code == 200:
                html = bs(response.text, "lxml")
                print("当前合集链接地址：", merge_url)
                tag_a = html.select("div#read_tpc a")  # 包含了图片的链接，需要剔除掉
                # import pdb;pdb.set_trace()
                if tag_a:  # 如果有
                    # print("种子链接有这么多个：",len(tag_a))
                    for tag in tag_a:
                        if re.compile("torrent").search(tag["href"]):  # 保留种子链接，剔除掉图片链接
                            torrent_url_queue.put({merge_name: tag["href"]})
                            print("该合集下种子链接：", tag["href"])
            # 有一个合集就下载一次
            get_torrent_infos_to_download()
            sleep(5)  # 睡 5 秒，切换集合
    except ConnectionError as e:
        print(e)
        parse_all_torrent_url()
"-----------------------------------文件操作----------------------------------------"
# 储存文件到该目录下(即储存路径)
def change_dir(folder_name):
    os.chdir("F://torrent/")  # 改变工作路径
    if not os.path.exists(folder_name):
        os.mkdir(folder_name)
        os.chdir(folder_name)
    else:
        os.chdir(folder_name)
    print("更改工作路径为：", os.getcwd())

# 传入名字用来穿件一个文件夹
# 用来根据合集创建文件夹
def mk_folder(folder_name):
    if not os.path.exists(folder_name):
        os.mkdir(folder_name)  # 创建分类文件夹
        print("文件夹创建成功：", folder_name)



""" ---------------------下载部分，可开多个线程 ----------------------------- """
# 获取一个种子文件的信息，包括最终下载地址
def get_torrent_infos_to_download():
    try:
        print("进入线程")
        while not torrent_url_queue.empty():
            print("进入了队列")
            for merge_name,torrent_url in torrent_url_queue.get().items():
                print("%s集合下：%s"%(merge_name,torrent_url))
                mk_folder(merge_name)   # 根据集合名字创建文件夹
                download_host = torrent_url.split("/")[2] # 用于拼接完整下载链接
                response = s.get(torrent_url)
                response.encoding = "utf-8"
                if response.status_code == 200:
                    print("访问成功：",torrent_url)
                    html = bs(response.text,"lxml")
                    name = html.select('title')[0].string.split(" ")[0]   # 文件名字
                    magnet = html.select(".uk-button")[0]["href"]    # 磁力链接
                    download_url = download_host+html.select(".uk-button")[1]["href"]   # torrent 链接
                    # 这里用来下载 磁力链接
                    download_magnet(magnet_url=magnet,filename=merge_name+"/"+name)
                    download_torrent(download_url=download_url,filename=merge_name+"/"+name)
                    torrent_url_queue.task_done()
                else:
                    print("网页访问失败！",response.status_code)
    except Exception as e:
        print("get_torrent_infos_to_download()出错啦,准备重试",e)
        get_torrent_infos_to_download()

# 下载磁力链接为 txt文件
def download_magnet(magnet_url,filename):
    with open(filename+".txt","w") as f:
        f.write(magnet_url)
# 下载图片
def download_img(image_url,filename):
    try:
        response = s.get(image_url)
        if response.status_code == 200:
            with open(filename+".jpeg","wb") as f:
                f.write(response.content)
        else:
            print("图片下载失败")
    except Exception:
        print("图片下载失败")
# 下载 torrent 文件
def download_torrent(download_url,filename):
    # 构造下载的请求头
    download_header = headers
    download_header['Referer'] = download_url
    download_header['Host'] = download_url.split("/")[2]

    response = s.get(url=download_url,headers=download_header,stream=True)
    print("下载中......",download_url)
    if os.path.exists(filename+".torrent"):
        print(filename+".torrent","已存在！")
    else:
        with open(filename+".torrent","wb") as f:
            for chunk in response.iter_content():
                f.write(chunk)
            print("下载成功：",filename+".torrent")

"""--------------------------------------解决验证码部分------------------------------------"""
class Captcha(object):
    def __init__(self,session,forbidden_url):
        self.session = session
        self.forbidden_url = forbidden_url
        self.pic_url = None
        self.pic_pwd = None

    # selenium获取验证码链接地址并返回
    # 传入需要验证码的url地址
    def __get_pic_link(self):
        print("验证码识别中...")
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        driver = webdriver.PhantomJS()
        driver.get(self.forbidden_url)

        try:
            element = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable ((By.ID, "recaptcha_widget"))
            )
            if element: #   验证码加载成功
                print("图片加载成功")
                pic_url = driver.find_element_by_css_selector("div#recaptcha_widget img")
                pic_id = driver.find_element_by_name("id").get_attribute("value")
                pic_captcha_challenge_field = driver.find_element_by_name("captcha_challenge_field").get_attribute("value")
                pic_params["id"] = pic_id
                pic_params["captcha_challenge_field"] = pic_captcha_challenge_field
                print("图片验证码地址为：",pic_url.get_attribute("src"))
                self.pic_url = pic_url.get_attribute("src")   # 获取验证码链接地址
            else:
                print("此页面不是验证码页面")
        except Exception:
            print("验证码处理出错，请检查代码！")
        finally:
            driver.quit()

    # 传入验证码的链接
    # 人为的判断，返回验证码
    def __get_pic_pwd(self):
        from PIL import Image
        response = requests.get(self.pic_url)
        with open("e:/pic.jpg",'wb') as file:
            file.write(response.content)
        Image.open("e:/pic.jpg").show()
        pic_password = input("请输入验证码：")
        os.remove("e:/pic.jpg")
        self.pic_pwd = pic_password


    # 验证码登录
    def __login(self):
        pic_pwd = self.pic_pwd
        pic_params["manual_captcha_challenge_field"] = pic_pwd
        response = self.session.get(pic_check_url,params=pic_params)
        if response.status_code ==  200:
            return True
        else:
            return False

    # 被外部调用的方法
    def captcha(self):
        self.__get_pic_link()
        self.__get_pic_pwd()
        status = self.__login()
        if status:
            print("恭喜你，验证码匹配成功！")
        else:
            print("验证码错误，请等待重试！")
            self.captcha()


def main():
    type_url = "http://1024.917rbb.biz/pw/thread.php?fid=5"     # 亚*五码
    type_name = "YZWM"
    change_dir(type_name)
    get_merge_info(type_url)    # 获取分类下的合集名称与地址
    parse_all_torrent_url()     # 遍历合集，将torrent链接添加到队列

if __name__ == '__main__':
    start = time()
    main()
    end = time()
    print("共耗时 {} s".format(end - start))
