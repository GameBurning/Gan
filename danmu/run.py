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
#import Danmu.python.record as record
import record


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
TRIPLE_SIX_DICT = {}
LUCKY_DICT = {}
AUDITION_DICT = {}
DOUYU_DICT = {}
ONLINE_FLAGS = {}
# LOCK = {}
ANALYSIS_DURATION = 45
THRESHOLD = 800
MAIN_THREAD_SLEEP_TIME = 5


class DanmuThread(threading.Thread):
    def __init__(self, roomID, name):
        threading.Thread.__init__(self)
        self.roomID = roomID
        self.name = name

    def run(self):
        print("===========DanmuThread on {} starts===========".format(self.name))
        try:
            (record_id, start_time) = record.start_record(self.roomID, block_size=ANALYSIS_DURATION)
            start_time = int(start_time)
        except Exception as e:
            print(e)
            return
        statistic_filename = str(self.roomID) + "_" + self.name + "_" + time.ctime(start_time) + ".csv"
        logdir = os.path.expanduser(LOGFILEDIR)
        danmu = []
        lucky = []
        douyu = []
        triple_six = []
        score_dict = []
        delete_range = []
        combine_range = []
        audition = []
        block_id = 0
        logfile = open(logdir + statistic_filename, 'w')
        logfile.write("time, block, danmu, 666, 学不来, 逗鱼时刻, audition\n")
        while ONLINE_FLAGS[self.roomID]:
            block_start_time = int(time.time())
            DANMU_DICT[self.roomID] = 0
            TRIPLE_SIX_DICT[self.roomID] = 0
            LUCKY_DICT[self.roomID] = 0
            DOUYU_DICT[self.roomID] = 0

            sleep_time = start_time + ANALYSIS_DURATION * (block_id + 1) - time.time()
            print('{}\'s wait time is :{}'.format(self.name, sleep_time))
            time.sleep(sleep_time)
            danmu.append(DANMU_DICT[self.roomID])
            lucky.append(LUCKY_DICT[self.roomID])
            douyu.append(DOUYU_DICT[self.roomID])
            triple_six.append(TRIPLE_SIX_DICT[self.roomID])
            audition.append(AUDITION_DICT[self.roomID])

            try:
                logfile.write("{},{},{},{},{},{},{}\n".format(block_start_time,
                                                              block_id, danmu[-1],
                                                              triple_six[-1],lucky[-1],
                                                              douyu[-1],audition[-1]))
                print("{}'s logfile: time:{}, block:{}, danmu:{}, 666:{}, gou:{}, douyu:{}, audition:{}"
                      .format(self.name, block_start_time, block_id, danmu[-1], triple_six[-1], lucky[-1],
                              douyu[-1], audition[-1]))
                logfile.flush()
            except Exception as e:
                print(e)

            block_score = triple_six[-1] * 8 + lucky[-1] * 12 + douyu[-1] * 20
            score_dict.append(block_score)

            print('{}\'s current block_id is {}'.format(self.name, block_id))
            if block_id >= 3:
                if douyu[-2] > 1 or score_dict[-2] >= THRESHOLD:
                    output_name = '{}_douyu{}_block{}to{}_score{}_lucky{}_triple{}' \
                        .format(self.name, douyu[-2], block_id - 3, block_id,
                                score_dict[-2],
                                lucky[-2],
                                triple_six[-2])
                    threading.Thread(target=record.combine_block,
                                     args=(record_id, block_id - 3, block_id, output_name)).start()
                threading.Thread(target=record.delete_block, args=(record_id, block_id - 3,
                                                                   block_id - 3)).start()
            block_id += 1
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
                roomInfos.append((line.split(':')[1].split('#')[0],
                                  line.split(':')[1].split('#')[1]))
    for (id, name) in roomInfos:
        ONLINE_FLAGS[id] = False
        AUDITION_DICT[id] = 0
    return roomInfos


def add_danmu(roomid, type):
    if type == "general":
        DANMU_DICT[roomid] += 1
    elif type == "666":
        TRIPLE_SIX_DICT[roomid] += 1
    elif type == "douyu":
        DOUYU_DICT[roomid] += 1
    else:
        LUCKY_DICT[roomid] += 1


def update_audition(roomid, audition_num):
    AUDITION_DICT[roomid] = audition_num


def room_is_online(room_id, name):
    # print("room:{} before requests time is:{}".format(room_id, time.ctime(time.time())))
    try:
        r = requests.get('http://room.api.m.panda.tv/index.php?\
                     method=room.shareapi&roomid=' + str(room_id), timeout=5)
    except:
        print(name + " timeout")
        return False
    # print("room:{} after requests time is:{}".format(room_id, time.ctime(time.time())))
    status = r.json()['data']['roominfo']['status']
    # TODO: Understand what does status 1 means
    if status == ONLINE_STATUS and int(r.json()['data']['roominfo']['person_num']) > 100:
        return True
    else:
        return False


def getChatInfo(roomid, name, osfile):
    print("===========getChatInfo on {} starts===========".format(name))
    try:
        f = urllib.request.urlopen(CHATINFOURL + roomid)
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
                    analyse_msg(s, totalLen, roomid, name, osfile)
                except Exception as e:
                    pass
    except Exception as e:
        print(e)
    print("===========getChatInfo on {} ends===========".format(name))


def analyse_msg(s, totalLen, roomid, name, osfile):
    while totalLen > 0:
        s.recv(IGNORE_LEN)
        recvLen = int.from_bytes(s.recv(META_LEN), 'big')
        recvMsg = s.recv(recvLen)
        # recv the whole msg.
        while recvLen > len(recvMsg):
            recvMsg = b''.join(recvMsg, s.recv(recvLen - len(recvMsg)))
        format_msg(recvMsg, roomid, name, osfile)
        totalLen = totalLen - IGNORE_LEN - META_LEN - recvLen


def format_msg(recvMsg, roomid, name, osfile):
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
                print(e)
                pass
            if identity == MANAGER:
                nickName = '*房管*' + nickName
            if identity == HOSTER:
                nickName = '*主播*' + nickName
            #识别表情
            emoji = re.match(r"(.*)\[:(.*)](.*)", content)
            if emoji:
                content = emoji.group(1) + '*' + emoji.group(2) + '*' + emoji.group(3)
            print(name + "_" + nickName + ":" + content)
            osfile.write(content + "\n")
            osfile.flush()
            add_danmu(roomid, "general")
            if '666' in content:
                add_danmu(roomid, "666")
            elif '学不来' in content or '狗' in content:
                add_danmu(roomid, "lucky")
            elif '时刻' in content:
                add_danmu(roomid, "douyu")
        elif jsonMsg['type'] == AUDIENCE_TYPE:
            print('==========={}\'s 观众人数'.format(name) + content + '==========')
            update_audition(roomid, content)
        else:
            pass
    except Exception as e:
        # print(recvMsg)
        pass


def main():
    roomInfos = loadInit()
    # for (id, name) in roomInfos:
    #     LOCK[id] = threading.Lock()
    while True:
        for (id, name) in roomInfos:
            online_status = room_is_online(id, name)
            if not ONLINE_FLAGS[id] and online_status:
                danmulog_filename = str(id) + "_" + name + "_Danmu" + ".txt"
                logdir = os.path.expanduser(LOGFILEDIR)
                f = open(logdir + danmulog_filename, 'a')
                ONLINE_FLAGS[id] = True
                threading.Thread(target=getChatInfo, args=(id, name, f)).start()
                DanmuThread(id, name).start()
                print("{} goes online".format(name))
            elif ONLINE_FLAGS[id] and not online_status:
                ONLINE_FLAGS[id] = False
                print("{} goes offline".format(name))
        time.sleep(MAIN_THREAD_SLEEP_TIME)


if __name__ == '__main__':
    main()
