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
ANALYSIS_DURATION = 45
MAIN_THREAD_SLEEP_TIME = 5

class DanmuThread(threading.Thread):
    def __init__(self, roomID, name):
        threading.Thread.__init__(self)
        self.roomID = roomID
        self.name = name

    def run(self):
        print("===========DanmuThread on {} starts===========".format(self.name))
        filename = str(self.roomID) + "_" + self.name + ".csv"
        logdir = os.path.expanduser(LOGFILEDIR)
        score_dict = []
        delete_range = []
        combine_range = []
        block_id = 0
        if os.path.isfile(logdir + filename):
            logfile = open(logdir + filename, 'a')
        else:
            logfile = open(logdir + filename, 'w')
            logfile.write("time, danmu, 666, 学不来, 逗鱼时刻, audition\n")
            logfile.flush()
        try:
            (record_id, start_time) = record.start_record(self.roomID, block_size=ANALYSIS_DURATION)
            start_time = int(start_time)
        except Exception:
            print(Exception)
            return
        while ONLINE_FLAGS[self.roomID]:
            block_start_time = int(time.time())
            DANMU_DICT[self.roomID].append(0)
            TRIPLE_SIX_DICT[self.roomID].append(0)
            LUCKY_DICT[self.roomID].append(0)
            DOUYU_DICT[self.roomID].append(0)
            sleep_time = start_time + ANALYSIS_DURATION * (block_id + 1) - time.time()
            print('{}\'s wait time is :{}'.format(self.name, sleep_time))
            time.sleep(sleep_time)

            try:
                logfile.write("{},{},{},{},{},{}\n".format(block_start_time, \
                                              DANMU_DICT[self.roomID][block_id], \
                                              TRIPLE_SIX_DICT[self.roomID][block_id],\
                                              LUCKY_DICT[self.roomID][block_id],\
                                              DOUYU_DICT[self.roomID][block_id],\
                                              AUDITION_DICT[self.roomID][block_id]))
                print("{}'s logfile: time:{}, danmu:{}, 666:{}, gou:{}, douyu:{}, audition:{}" \
                      .format(self.name, block_start_time, \
                              DANMU_DICT[self.roomID][block_id], \
                              TRIPLE_SIX_DICT[self.roomID][block_id], \
                              LUCKY_DICT[self.roomID][block_id], \
                              DOUYU_DICT[self.roomID][block_id], \
                              AUDITION_DICT[self.roomID][block_id]))
                logfile.flush()
            except Exception as e:
                print(e)


            block_score = TRIPLE_SIX_DICT[self.roomID] * 8 + LUCKY_DICT[self.roomID] * 12 + \
                          DOUYU_DICT[self.roomID] * 20
            score_dict.append(block_score)

            print('{}\'s current block_id is {}'.format(self.name, block_id))
            if block_id >= 2:
                if score_dict[-2] >= 60:
                    if combine_range != [] and block_id - 2 <= combine_queue[1] and \
                                            combine_queue[1] - combine_queue[0] < 10:
                        combine_queue[1] = block_id
                    else:
                        output_name = '{}_block{}to{}_score{}_lucky{}_douyu{}_triple{}' \
                            .format(self.name, combine_queue[0], combine_queue[1], \
                                    score_dict[combine_queue[0] + 1],\
                                    LUCKY_DICT[self.roomID][combine_queue[0] + 1], \
                                    DOUYU_DICT[self.roomID][combine_queue[0] + 1], \
                                    TRIPLE_SIX_DICT[self.self.roomID][combine_queue[0] + 1])
                        threading.Thread(target=record.combine_block, \
                                         args=(record_id, combine_queue[0], combine_queue[1], output_name)).start()
                        combine_queue = [block_id - 2, block_id]

                if block_id >= 3 and delete_range[-1][-1] == block_id - 3 and delete_range[1] - delete_range[0] < 10:
                    delete_range[-1][-1] = block_id - 2
                else:
                    threading.Thread(target=record.delete_block, args=(record_id, [delete_range[0]], delete_range[1]))
                    delete_range = [block_id - 2, block_id - 2]

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
                roomInfos.append((line.split(':')[1].split('#')[0], \
                                  line.split(':')[1].split('#')[1]))
    for (id, name) in roomInfos:
        ONLINE_FLAGS[id] = False
        AUDITION_DICT[id] = 0
    return roomInfos


def add_danmu(roomid, type):
    if type == "general":
        DANMU_DICT[roomid][-1] += 1
    elif type == "666":
        TRIPLE_SIX_DICT[roomid][-1] += 1
    elif type == "douyu":
        DOUYU_DICT[roomid][-1] += 1
    else:
        LUCKY_DICT[roomid][-1] += 1


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
    if status == OFFLINE_STATUS:
        return False
    else:
        return True


def getChatInfo(roomid, name):
    print("===========getChatInfo on {} starts===========".format(name))

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
                    analyseMsg(s, totalLen, roomid, name)
                except Exception as e:
                    pass
    print("===========getChatInfo on {} ends===========".format(name))


def analyseMsg(s, totalLen, roomid, name):
    while totalLen > 0:
        s.recv(IGNORE_LEN)
        recvLen = int.from_bytes(s.recv(META_LEN), 'big')
        recvMsg = s.recv(recvLen)
        # recv the whole msg.
        while recvLen > len(recvMsg):
            recvMsg = b''.join(recvMsg, s.recv(recvLen - len(recvMsg)))
        formatMsg(recvMsg, roomid, name)
        totalLen = totalLen - IGNORE_LEN - META_LEN - recvLen


def formatMsg(recvMsg, roomid, name):
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
            print(name + "_" + nickName + ":" + content)
            add_danmu(roomid, "general")
            if '666' in content:
                add_danmu(roomid, "666")
            elif '学不来' in content or '狗' in content:
                add_danmu(roomid, "lucky")
            elif '时刻' in content:
                add_danmu(roomid, "douyu")
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
            online_status = room_is_online(id, name)
            if not ONLINE_FLAGS[id] and online_status:
                ONLINE_FLAGS[id] = True
                DANMU_DICT[id] = []
                TRIPLE_SIX_DICT[id] = []
                LUCKY_DICT[id] = []
                AUDITION_DICT[id] = []
                DOUYU_DICT[id] = []
                threading.Thread(target=getChatInfo, args=(id, name)).start()
                DanmuThread(id, name).start()
            elif ONLINE_FLAGS[id] and not online_status:
                ONLINE_FLAGS[id] = False
            print("{} is {}".format(name, "online" if online_status else "offline"))
        time.sleep(MAIN_THREAD_SLEEP_TIME)


if __name__ == '__main__':
    main()
