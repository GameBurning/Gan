import json
import time
import requests
import pprint
import re


live_info_store = {
    "panda.tv" : { "key" : "value" },
    "zhanqi.tv" : { "key" : "value" }
}

def get_stream_url(platform, room_id):
    print("get_stream_by_room")
    stream_urls = []
    plflag = None
    host_rid = None
    host_name = None
    room_name = None
    room_category = None
    room_start_time = None
    room_status = None
    video_id = None

    r = requests.get("http://www.panda.tv/api_room_v3?roomid={}&__plat=pc_web&_={}".format(room_id, int(time.time())))
    pp = pprint.PrettyPrinter(indent=4)
    response = None
    if r.status_code == 200:
        response = json.loads(r.text)
    pp.pprint(response)
    errno = response["errno"]
    errmsg = response["errmsg"]
    if errno != "0" and errno != 0:
        raise ValueError("Errno : {}, Errmsg : {}".format(errno, errmsg))
    data = response["data"]

    plflag = data["videoinfo"]["plflag"].split("_")


    r_2 = requests.get("http://room.api.m.panda.tv/index.php?method=room.shareapi&roomid={}".format(room_id))
    response_2 = None
    if r_2.status_code == 200:
        response_2 = json.loads(r_2.text)
    pp.pprint(response_2)
    errno = response_2["errno"]
    errmsg = response_2["errmsg"]
    if errno != "0" and errno != 0:
        raise ValueError("Errno : {}, Errmsg : {}".format(errno, errmsg))
    data_2 = response_2["data"]
    host_rid = data_2["hostinfo"]["rid"]
    host_name = data_2["hostinfo"]["name"]

    room_name = data_2["roominfo"]["name"]
    room_category = data_2["roominfo"]["cate"]
    room_start_time = data_2["roominfo"]["start_time"]
    room_status = data_2["roominfo"]["status"]

    if room_status is not "2":
        raise ValueError("The live stream is not online! (status:%s)" % room_status)

    # "http://pl-hls3.live.panda.tv/live_panda/7d9bdfd8beca4be796bc4b757503decd_small.m3u8",
    title_search = re.search('.*/live_panda/(.*)(_small)?.m3u8', data_2["videoinfo"]["address"], re.IGNORECASE)

    if title_search:
        video_id = title_search.group(1)
    print("videoID: " + str(video_id))

    real_url = "http://pl{}.live.panda.tv/live_panda/{}.flv".format(plflag[1], video_id)
    stream_urls.append(real_url)

    pp.pprint(stream_urls)

    return stream_urls
