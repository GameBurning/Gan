#Panda TV

###房间信息API：
```
Methond: GET
```
```
URL:http://room.api.m.panda.tv/index.php?
```
```
params(URL encoded):
method = "room.shareapi"
roomid = {roomId}
_ = {jsTimeStamp}

```
```
Response: JSON

```

```
Example:
REQUEST: 
http://room.api.m.panda.tv/index.php?
method=room.shareapi&roomid=27337&_=1478754719396
RESPONSE:
{
  "errno": "0",
  "errmsg": "",
  "data": {
    "hostinfo": {
      "rid": "3252620",
      "name": "熊丶猫TV小新",
      "avatar": "http://i9.pdim.gs/826ef7a8179b0b3eece5a019775def0c.jpg",
      "bamboos": "72616092"
    },
    "roominfo": {
      "id": "27337",
      "name": "没有什么事是一枪解决不了的！",
      "classification": "英雄联盟",
      "cate": "lol",
      "bulletin": "新浪微博：熊猫TV小新 粉丝群：464033802 房管群：559478525 麻烦各位房管加下\n长期不加群房管可能会被撤销哦",
      "person_num": "206152",
      "fans": "690597",
      "pictures": {
        "img": "http://i9.pdim.gs/45/1b77c5d4e6d554c32aa107846c3dd471/w338/h190.jpg"
      },
      "display_type": "1",
      "start_time": "1478745088",
      "end_time": "1478698288",
      "room_type": "1",
      "status": "2"
    },
    "videoinfo": {
      "address": "http://pl-hls8.live.panda.tv/live_panda/4b0904bbdb295b039405d8a7879ae43b_small.m3u8",
      "watermark": "1"
    }
  },
  "authseq": ""
}
```

###视频地址：
```
在房间信息API的response里videoinfo的address就是vlc可处理的playlist文件
```
```
Example:
http://pl-hls8.live.panda.tv/live_panda/4b0904bbdb295b039405d8a7879ae43b_small.m3u8
```
