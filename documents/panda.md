#Panda TV

##房间信息API：
```
Methond: GET
```
```
URL:   http://room.api.m.panda.tv/index.php
```
```
params(URL encoded):

method = "room.shareapi"
roomid = [roomId]
_ = [jsTimeStamp]

```
```
Response:JSON
Example:

REQUEST:  http://room.api.m.panda.tv/index.php?
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

##视频地址：
在房间信息API的response里videoinfo的address就是vlc可处理的m3u8格式的playlist文件。但是我们可以用同样的文件名去访问这个地址的flv格式的文件，flv格式用ffmpeg保存更好。

比如在房间信息API中获取的地址是这样的：
```json
 {"videoinfo": { "address": "http://pl-hls3.live.panda.tv/live_panda/a60c08c3c87fe77d3541f2b91fe0b3d7_small.m3u8","watermark": "4"}}
```
我们把:a60c08c3c87fe77d3541f2b91fe0b3d7提出来放进这个flv的地址里：
```
http://220.243.194.31/pl3.live.panda.tv/live_panda/a60c08c3c87fe77d3541f2b91fe0b3d7.flv
```
或者这里：
```
pl12.live.panda.tv/live_panda/a60c08c3c87fe77d3541f2b91fe0b3d7.flv
```


可用ffmpeg指令来下载以上flv地址的视频。

可用的CDN地址有：

- (always) **pl12.live.panda.tv/live_panda/xxx.flv**
- (optional) 220.243.194.31
- (optional) 220.243.194.32
- (optional) 203.131.253.35
- (optional) 203.131.253.34
- (optional) 220.243.225.50
- (optional) 220.243.194.30
- (optional) 183.232.7.190
- (optional) 107.155.46.141 


pl12.live.panda.tv/live_panda/c4e599ce9e9a3efa1c51024a1b1b86f7.flv
