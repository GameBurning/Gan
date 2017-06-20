import json
import time
import requests
import pprint
import re
import hashlib
import uuid
import random
import urllib.parse, urllib.request
from bs4 import BeautifulSoup

import dyprvt
API_KEY = 'a2053899224e8a92974c729dceed1cc99b3d8282'
VER = '2017061511'

def dyprvt_hash(input_data):
    return dyprvt.stupidMD5(input_data)


def get_stream_huya(room_id):
    stream_urls = []
    # r = requests.get("http://www.huya.com/{}".format(room_id))
    # if r.status_code != 200:
    #     return []
    # htmlContent = r.text
    # soup = BeautifulSoup(htmlContent, 'html.parser')
    # print(soup.prettify())
    # list = soup.find_all("script")
    # url = ""
    #
    # for item in list:
    #     if "TT_ROOM_DATA" in item.text:
    #         str = item.text
    #         m = re.search('var TT_ROOM_DATA = (.*?);', str)
    #         v = m.groups()
    #         u = v[0]
    #         j = json.loads(u)
    #         previewUrl = j['previewUrl']
    #         previewUrl = previewUrl.replace("_100/playlist.m3u8", "_800/playlist.m3u8")
    #         stream_urls.append(previewUrl)
    #         print(previewUrl)

    return stream_urls

def get_stream_zhanqi(room_id):
    stream_urls = []

    api_url = "https://www.zhanqi.tv/api/static/v2.1/room/domain/" + room_id + ".json"
    try:
        r = requests.get("https://www.zhanqi.tv/api/static/v2.1/room/domain/{}.json".format(room_id), timeout=3)
        if r.status_code != 200:
            return []
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(r.text)

        j = json.loads(r.text)
        data = j['data']
        status = data['status']
        roomid = data['id']
        videoId = data['videoId']
    except:
        return []

    if status != '4':
        raise ValueError ("The live stream is not online!")

    url = "https://livedns.yfcloud.com/d?host=yfhdl.cdn.zhanqi.tv&stream={}_720p.flv".format(videoId)
    # jump_url = "http://wshdl.load.cdn.zhanqi.tv/zqlive/{}.flv?get_url=1".format(videoId)
    r = requests.get(url, timeout=3)
    if r.status_code != 200:
        return []

    j = json.loads(r.text)
    ips = j['ips']
    for ip in ips:
        url = "http://{}/yfhdl.cdn.zhanqi.tv/zqlive/{}_720p.flv?device=0".format(ip,videoId)
        stream_urls.append(url)

    return stream_urls

def get_stream_douyu(room_id):
    stream_urls = []
    cdn='ws'
    rate='2'
    endpoint = 'https://www.douyu.com/lapi/live/getPlay/' + room_id
    tt = str(int(time.time() / 60))
    rnd_md5 = hashlib.md5(str(random.random()).encode('utf8'))
    did = rnd_md5.hexdigest().upper()
    to_sign = ''.join([room_id, did, API_KEY, tt])
    sign = dyprvt_hash(to_sign)
    payload = dict(ver=VER, sign=sign, did=did, rate=rate, tt=tt, cdn=cdn)

    json_data = requests.post(endpoint, data=payload).json()

    if json_data['error'] == 0:
        data = json_data['data']
        url = '/'.join([data['rtmp_url'], data['rtmp_live']])
        stream_urls.append(url)
    elif json_data['error'] == -5:
        raise Exception('Offline')
    else:
        raise Exception('API returned with error {}'.format(json_data['error']))

    return stream_urls

def get_stream_panda(room_id):
    stream_urls = []
    plflag = None
    host_rid = None
    host_name = None
    room_name = None
    room_category = None
    room_start_time = None
    room_status = None
    video_id = None
    try:
        r = requests.get("http://www.panda.tv/api_room_v3?roomid={}&__plat=pc_web&_={}".format(room_id, int(time.time())), timeout=5)
    except:
        print("cannot get response from room info API\n")
        return []
    pp = pprint.PrettyPrinter(indent=4)
    response = None
    if r.status_code == 200:
        response = json.loads(r.text)
    # pp.pprint(response)
    errno = response["errno"]
    errmsg = response["errmsg"]
    if errno != "0" and errno != 0:
        print("!!Errno : {}, Errmsg : {}".format(errno, errmsg))
        return []
    data = response["data"]

    plflag = data["videoinfo"]["plflag"].split("_")

    try:
        r_2 = requests.get("http://room.api.m.panda.tv/index.php?method=room.shareapi&roomid={}".format(room_id), timeout=3)
    except:
        return []
    response_2 = None
    if r_2.status_code == 200:
        response_2 = json.loads(r_2.text)
    # pp.pprint(response_2)
    errno = response_2["errno"]
    errmsg = response_2["errmsg"]
    if errno != "0" and errno != 0:
        print("!!Errno : {}, Errmsg : {}".format(errno, errmsg))
        return []
    data_2 = response_2["data"]
    host_rid = data_2["hostinfo"]["room_id"]
    host_name = data_2["hostinfo"]["name"]

    room_name = data_2["roominfo"]["name"]
    room_category = data_2["roominfo"]["cate"]
    room_start_time = data_2["roominfo"]["start_time"]
    room_status = data_2["roominfo"]["status"]

    if room_status is not '2':
        print("!!Errno : The live stream is NOT ONLINE!")
        return []

    # "http://pl-hls3.live.panda.tv/live_panda/7d9bdfd8beca4be796bc4b757503decd_small.m3u8",
    title_search = re.search('.*/live_panda/([0-9A-Za-z]*)(_small)?.m3u8', data_2["videoinfo"]["address"], re.IGNORECASE)

    if title_search:
        video_id = title_search.group(1)
        real_url_main = "http://pl{}.live.panda.tv/live_panda/{}.flv".format(plflag[1], video_id)
        stream_urls.append(real_url_main)
        if len(plflag) >= 2:
            real_url_backup = "http://pl{}.live.panda.tv/live_panda/{}.flv".format(plflag[0], video_id)
            stream_urls.append(real_url_backup)
        pp.pprint(stream_urls)
    else:
        print("cannot extract video id from url: " + str(data_2["videoinfo"]["address"]))

    return stream_urls

live_info_store = {
    "panda" : { "stream_url_func" : get_stream_panda },
    "douyu" : { "stream_url_func" : get_stream_douyu },
    "zhanqi" : { "stream_url_func" : get_stream_zhanqi },
    "huya" : {"stream_url_func" : get_stream_huya}
}


def get_stream_url(platform, room_id):
    print("get_stream_url")
    return live_info_store[platform]['stream_url_func'](room_id)
