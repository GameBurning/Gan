import time, sys, re, json
import socket, select
import threading
import urllib
import platform

import requests

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
INIT_PROPERTIES = 'init1.properties'
MANAGER = '60'
SP_MANAGER = '120'
HOSTER = '90'

class _socket(socket.socket):
    def communicate(self, data):
        self.push(data)
        return self.pull()
    def push(self, data):
        self.sendall(data)
    def pull(self):
        try: # for socket.settimeout
            return self.recv(9999)
        except:
            return ''


class PandaDanMuClient():
    # return if the room is Online
    def __init__(self, room_id, name, count_danmu_fn, maxNoDanMuWait = 180, anchorStatusRescanTime = 30):
        self.roomID = room_id
        self.name = name
        self.maxNoDanMuWait = maxNoDanMuWait
        self.anchorStatusRescanTime = anchorStatusRescanTime
        self.deprecated = False  # this is an outer live flag
        self.live = False  # this is an inner live flag
        self.danmuSocket = None
        self.danmuThread, self.heartThread = None, None
        self.danmuWaitTime = -1
        self.danmuProcess = None
        self.countDanmuFn = count_danmu_fn

    def start(self):
        print("===========Socket thread of {} starts===========".format(self.name))
        while not self.deprecated:
            try:
                f = urllib.request.urlopen('http://riven.panda.tv/chatroom/getinfo?roomid=' + self.roomID)
                data = f.read().decode('utf-8')
                chatInfo = json.loads(data)
                chatAddr = chatInfo['data']['chat_addr_list'][0]
                socketIP = chatAddr.split(':')[0]
                socketPort = int(chatAddr.split(':')[1])
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((socketIP, socketPort))
                rid = str(chatInfo['data']['rid']).encode('utf-8')
                appid = str(chatInfo['data']['appid']).encode('utf-8')
                authtype = str(chatInfo['data']['authType']).encode('utf-8')
                sign = str(chatInfo['data']['sign']).encode('utf-8')
                ts = str(chatInfo['data']['ts']).encode('utf-8')
                msg = b'u:' + rid + b'@' + appid + b'\nk:1\nt:300\nts:' + ts \
                      + b'\nsign:' + sign + b'\nauthtype:' + authtype
                msgLen = len(msg)
                sendMsg = b'\x00\x06\x00\x02' + int.to_bytes(msgLen, 2, 'big') + msg
                s.sendall(sendMsg)
                recvMsg = s.recv(CHECK_LEN)
                if recvMsg == FIRST_RPS:
                    print('成功连接弹幕服务器')
                    recvLen = int.from_bytes(s.recv(2), 'big')
                    s.recv(recvLen)

                def keepalive():
                    while not self.deprecated:
                        # print('================keepalive=================')
                        s.send(KEEPALIVE)
                        time.sleep(150)

                threading.Thread(target=keepalive).start()

                while not self.deprecated:
                    # print('================receive messages=================')
                    recvMsg = s.recv(CHECK_LEN)
                    if recvMsg == RECVMSG:
                        recvLen = int.from_bytes(s.recv(2), 'big')
                        recvMsg = s.recv(recvLen)  # ack:0
                        totalLen = int.from_bytes(s.recv(META_LEN), 'big')
                        try:
                            self.analyse_msg(s, totalLen)
                        except Exception as e:
                            pass
            except Exception as e:
                print(e)
            time.sleep(1)
            print("===========Socket thread of {} ends===========".format(self.name))

    def analyse_msg(self, s, totalLen):
        while totalLen > 0:
            s.recv(IGNORE_LEN)
            recvLen = int.from_bytes(s.recv(META_LEN), 'big')
            recvMsg = s.recv(recvLen)
            # recv the whole msg.
            while recvLen > len(recvMsg):
                recvMsg = b''.join(recvMsg, s.recv(recvLen - len(recvMsg)))
            self.format_msg(recvMsg)
            totalLen = totalLen - IGNORE_LEN - META_LEN - recvLen

    def format_msg(self, recvMsg, roomid, name, osfile):
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
                # 识别表情
                emoji = re.match(r"(.*)\[:(.*)](.*)", content)
                if emoji:
                    content = emoji.group(1) + '*' + emoji.group(2) + '*' + emoji.group(3)
                print(name + "_" + nickName + ":" + content)
                osfile.write(content + "\n")
                osfile.flush()
                self.countDanmuFn(content)
            elif jsonMsg['type'] == AUDIENCE_TYPE:
                print('==========={}\'s 观众人数'.format(name) + content + '==========')
            else:
                pass
        except Exception as e:
            # print(recvMsg)
            pass