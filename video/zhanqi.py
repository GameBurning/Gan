import json
import time
import requests
import pprint
import re

def zhanqi_download(room_id):
    stream_urls = []
    api_url = "https://www.zhanqi.tv/api/static/v2.1/room/domain/" + room_id + ".json"
    try:
        r = requests.get(api_url , timeout=3)
    except:
        return []

    api_json = json.loads(r.text)
    data = api_json['data']
    status = data['status']

    if status != '4':
        raise ValueError ("The live stream is not online!")

    nickname = data['nickname']
    title = nickname + ": " + data['title']

    roomid = data['id']
    videoId = data['videoId']
    jump_url = "http://wshdl.load.cdn.zhanqi.tv/zqlive/" + videoId + ".flv?get_url=1"
    jump_url = jump_url.strip('\r\n')

    try:
        r = requests.get(jump_url , timeout=3)
    except:
        return []
    real_url = r.text
    real_url = real_url.strip('\r\n')

    stream_urls.append(real_url)

    print(".......... urls : " + str(stream_urls))

if __name__ == "__main__":
    zhanqi_download("lipeng")
