import json
import time
import requests
import pprint
import re
import hashlib

def get_stream_zhanqi(room_id):
    return []

def get_stream_douyu(room_id):
    stream_urls = []
    try:
        r = requests.get("http://m.douyu.com/html5/live?roomId={}".format(room_id), timeout=3)
    except:
        return []
    if r.status_code != 200:
        return []

    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(r.text)
    if 'data' not in json.loads(r.text):
        return stream_urls
    data = json.loads(r.text)['data']
    server_status = data.get('error',0)
    if server_status is not 0:
        raise ValueError("Server returned error:%s" % server_status)

    title = data.get('room_name')
    show_status = data.get('show_status')
    print("show_status : " + show_status)
    if show_status is not "1":
        raise ValueError("The live stream is not online! (Errno:%s)" % server_status)

    tt = int(time.time())
    sign_content = 'lapi/live/thirdPart/getPlay/{}?aid=pcclient&rate=0&time={}9TUk5fjjUjg9qIMH3sdnh'.format(room_id, tt)
    sign = hashlib.md5(sign_content.encode('ascii')).hexdigest()

    json_request_url = "http://coapi.douyucdn.cn/lapi/live/thirdPart/getPlay/{}?rate=0".format(room_id)
    headers = {'auth': sign, 'time': str(tt), 'aid': 'pcclient'}

    try:
        r = requests.get(json_request_url,  headers = headers, timeout=3)
    except:
        return []
    if r.status_code != 200:
        return []
    data = json.loads(r.text)['data']
    server_status = data.get('error',0)

    if server_status is not 0:
        raise ValueError("Server returned error:%s" % server_status)

    real_url = data.get('live_url')
    stream_urls.append(real_url)
    print("........... urls : " + str(stream_urls))

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
        r = requests.get("http://www.panda.tv/api_room_v3?roomid={}&__plat=pc_web&_={}".format(room_id, int(time.time())), timeout=3)
    except:
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
    host_rid = data_2["hostinfo"]["rid"]
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
    "zhanqi" : { "stream_url_func" : get_stream_zhanqi }
}


def get_stream_url(platform, room_id):
    print("get_stream_url")
    return live_info_store[platform]['stream_url_func'](room_id)
