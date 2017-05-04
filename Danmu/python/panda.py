#!/usr/bin/env python3
import urllib.request
import socket
import json
import time
import threading
import os
import platform
import re
import requests

CHATINFOURL = 'http://riven.panda.tv/chatroom/getinfo?roomid='
CHATROOMAPI = 'http://room.api.m.panda.tv/index.php?method=room.shareapi&roomid='
LOGFILEDIR = '~/pandaLog/'
IGNORE_LEN = 12
META_LEN = 4
CHECK_LEN = 4
FIRST_REQ = b'\x00\x06\x00\x02'
FIRST_RPS = b'\x00\x06\x00\x06'
KEEPALIVE = b'\x00\x06\x00\x00'
RECVMSG = b'\x00\x06\x00\x03'
DANMU_TYPE = '1'
BAMBOO_TYPE = '206'
AUDIENCE_TYPE = '207'
TU_HAO_TYPE = '306'
SYSINFO = platform.system()
INIT_PROPERTIES = 'init.properties'
MANAGER = '60'
SP_MANAGER = '120'
HOSTER = '90'
OFFLINE_STATUS = '3'
ONLINE_STATUS = '2'

DANMU_DICT = {}
AUDITION_DICT = {}
ONLINE_FLAGS = {}

class DanmuThread(threading.Thread):
    def __init__(self, roomID, name):
        threading.Thread.__init__(self)
        self.roomID = roomID
        self.name = name
    def run(self):
        print("===========DanmuThread on {} starts===========".format(self.name))
        filename = str(self.roomID) + "_" + self.name + ".csv"
        logdir = os.path.expanduser(LOGFILEDIR)
        # getChatInfo(self.roomID)
        if os.path.isfile(logdir + filename):
            logfile = open(logdir + filename, 'a')
        else:
            logfile = open(logdir + filename, 'w')
            logfile.write("time, danmu_number, audition_number\n")
        while ONLINE_FLAGS[self.roomID]:
            print("{} time 1 is :{}".format(self.name, time.ctime(time.time())))
            start_time = int(time.time())
            DANMU_DICT[self.roomID] = 0
            print("{} time 2 is :{}".format(self.name, time.ctime(time.time())))
            time.sleep(5)
            print("{} time 3 is :{}".format(self.name, time.ctime(time.time())))
            logfile.write("{},{},{}\n".format(start_time, DANMU_DICT[self.roomID], \
                                                  AUDITION_DICT[self.roomID]))
            print("{} time 4 is :{}".format(self.name, time.ctime(time.time())))
            print("{} logfile:{},{},{}".format(self.name, start_time, DANMU_DICT[self.roomID], \
                                          AUDITION_DICT[self.roomID]))

        #ONLINE_FLAGS[self.roomID] = False
        logfile.close()
        print("===========Thread on {} ends===========".format(self.name))


def loadInit()->[]:
    roomInfos = []
    with open(INIT_PROPERTIES, 'r') as f:
        init = f.read()
        init = init.split('\n')
        for line in init:
            if len(line.split(':')) == 2:
                #[(roomID, name)]
                roomInfos.append((line.split(':')[1].split('#')[0], line.split(':')[1].split('#')[1]))
    for (id, name) in roomInfos:
        ONLINE_FLAGS[id] = False
        AUDITION_DICT[id] = 0
    return roomInfos


def add_danmu(roomid):
    DANMU_DICT[roomid] += 1

def update_audition(roomid, audition_num):
    AUDITION_DICT[roomid] = audition_num

def room_is_online(room_id):
    # print("room:{} before requests time is:{}".format(room_id, time.ctime(time.time())))
    try:
        r = requests.get('http://room.api.m.panda.tv/index.php?\
                     method=room.shareapi&roomid=' + str(room_id), timeout=5)
    except:
        print("timeout")
        return False
    # print("room:{} after requests time is:{}".format(room_id, time.ctime(time.time())))
    status = r.json()['data']['roominfo']['status']
    # TODO: Understand what does status 1 means
    if status == OFFLINE_STATUS:
        return False
    else:
        return True


def getChatInfo(roomid, name):
    print("===========getChatInfo on {} starts===========".format(name))
    danmuThread = DanmuThread(roomid, name)
    danmuThread.start()
    with urllib.request.urlopen(CHATINFOURL + roomid) as f:
        data = f.read().decode('utf-8')
        chatInfo = json.loads(data)
        chatAddr = chatInfo['data']['chat_addr_list'][0]
        socketIP = chatAddr.split(':')[0]
        socketPort = int(chatAddr.split(':')[1])
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((socketIP,socketPort))
        rid      = str(chatInfo['data']['rid']).encode('utf-8')
        appid    = str(chatInfo['data']['appid']).encode('utf-8')
        authtype = str(chatInfo['data']['authType']).encode('utf-8')
        sign     = str(chatInfo['data']['sign']).encode('utf-8')
        ts       = str(chatInfo['data']['ts']).encode('utf-8')
        msg  = b'u:' + rid + b'@' + appid + b'\nk:1\nt:300\nts:' + ts\
        + b'\nsign:' + sign + b'\nauthtype:' + authtype
        msgLen = len(msg)
        sendMsg = FIRST_REQ + int.to_bytes(msgLen, 2, 'big') + msg
        s.sendall(sendMsg)
        recvMsg = s.recv(CHECK_LEN)
        if recvMsg == FIRST_RPS:
            print('成功连接弹幕服务器')
            recvLen = int.from_bytes(s.recv(2), 'big')
            s.recv(recvLen)
        def keepalive():
            while ONLINE_FLAGS[roomid]:
                # print('================keepalive=================')
                s.send(KEEPALIVE)
                time.sleep(150)
        threading.Thread(target=keepalive).start()

        while ONLINE_FLAGS[roomid]:
            # print('================receive messages=================')
            recvMsg = s.recv(CHECK_LEN)
            if recvMsg == RECVMSG:
                recvLen = int.from_bytes(s.recv(2), 'big')
                recvMsg = s.recv(recvLen)   #ack:0
                totalLen = int.from_bytes(s.recv(META_LEN), 'big')
                try:
                    analyseMsg(s, totalLen, roomid)
                except Exception as e:
                    pass
    print("===========getChatInfo on {} ends===========".format(name))


def analyseMsg(s, totalLen, roomid):
    while totalLen > 0:
        s.recv(IGNORE_LEN)
        recvLen = int.from_bytes(s.recv(META_LEN), 'big')
        recvMsg = s.recv(recvLen)
        # recv the whole msg.
        while recvLen > len(recvMsg):
            recvMsg = b''.join(recvMsg, s.recv(recvLen - len(recvMsg)))
        formatMsg(recvMsg, roomid)
        totalLen = totalLen - IGNORE_LEN - META_LEN - recvLen


def formatMsg(recvMsg, roomid):
    try:
        jsonMsg = eval(recvMsg)
        content = jsonMsg['data']['content']
        if jsonMsg['type'] == DANMU_TYPE:
            identity = jsonMsg['data']['from']['identity']
            nickName = jsonMsg['data']['from']['nickName']
            try:
                spIdentity = jsonMsg['data']['from']['sp_identity']
                if spIdentity == SP_MANAGER:
                    nickName = '*超管*' + nickName
            except Exception as e:
                pass
            if identity == MANAGER:
                nickName = '*房管*' + nickName
            if identity == HOSTER:
                nickName = '*主播*' + nickName
            #识别表情
            emoji = re.match(r"(.*)\[:(.*)](.*)", content)
            if emoji:
                content = emoji.group(1) + '*' + emoji.group(2) + '*' + emoji.group(3)
            # print(nickName + ":" + content)
            add_danmu(roomid)
        # elif jsonMsg['type'] == BAMBOO_TYPE:
        #     nickName = jsonMsg['data']['from']['nickName']
        #     print(nickName + "送给主播[" + content + "]个竹子")
        #     notify(nickName, "送给主播[" + content + "]个竹子")
        # elif jsonMsg['type'] == TU_HAO_TYPE:
        #     nickName = jsonMsg['data']['from']['nickName']
        #     price = jsonMsg['data']['content']['price']
        #     print('*********' + nickName + "送给主播[" + price + "]个猫币" + '**********')
        #     notify(nickName, "送给主播[" + price + "]个猫币")
        elif jsonMsg['type'] == AUDIENCE_TYPE:
            print('===========观众人数' + content + '==========')
            update_audition(roomid, content)
        else:
            pass
    except Exception as e:
        # print(recvMsg)
        pass


def main():
    roomInfos = loadInit()
    while True:
        for (id, name) in roomInfos:
            if not ONLINE_FLAGS[id] and room_is_online(id):
                ONLINE_FLAGS[id] = True
                threading.Thread(target=getChatInfo, args=(id, name)).start()
            elif ONLINE_FLAGS[id] and not room_is_online(id):
                ONLINE_FLAGS[id] = False
        time.sleep(30)


if __name__ == '__main__':
    main()
