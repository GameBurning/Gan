import time, sys, re, json
import socket, select
from struct import pack

import requests

from .Abstract import AbstractDanMuClient


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


class PandaDanMuClient(AbstractDanMuClient):
    # return if the room is Online
    def get_live_status(self):
        try:
            j = requests.get('http://room.api.m.panda.tv/index.php?method=room.shareapi&roomid='
                             + str(self.roomID), timeout=5).json()
        except:
            print(self.name + " timeout")
            return False
        try:
            return j['data']['roominfo']['status'] == '2'
        except json.decoder.JSONDecodeError as e:
            print("Inside Panda get_live Function: {}. Json is {}".format(e, j))
            return False
        except Exception as e:
            print("Inside Panda get_live Function:{}. Json is {}".format(e))

    # return (danmuSocketInfo), roomInfo
    def _prepare_env(self):
        url = 'http://www.panda.tv/ajax_chatroom?roomid=%s&_=%s'%(self.roomID, str(int(time.time())))
        roomInfo = requests.get(url).json()
        url = 'http://api.homer.panda.tv/chatroom/getinfo'
        params = {
            'rid': roomInfo['data']['rid'],
            'roomid': self.roomID,
            'retry': 0,
            'sign': roomInfo['data']['sign'], 
            'ts': roomInfo['data']['ts'],
            '_': int(time.time()), }
        serverInfo = requests.get(url, params).json()['data']
        serverAddress = serverInfo['chat_addr_list'][0].split(':')
        return (serverAddress[0], int(serverAddress[1])), serverInfo


    def _init_socket(self, danmu, roomInfo):
        data = [
            ('u', '%s@%s'%(roomInfo['rid'], roomInfo['appid'])),
            ('k', 1),
            ('t', 300),
            ('ts', roomInfo['ts']),
            ('sign', roomInfo['sign']),
            ('authtype', roomInfo['authType']) ]
        data = '\n'.join('%s:%s'%(k, v) for k, v in data)
        data = (b'\x00\x06\x00\x02\x00' + pack('B', len(data)) +
            data.encode('utf8') + b'\x00\x06\x00\x00')
        self.danmuSocket = _socket(socket.AF_INET, socket.SOCK_STREAM)
        self.danmuSocket.settimeout(3)
        self.danmuSocket.connect(danmu)
        self.danmuSocket.push(data)
    def _create_thread_fn(self, roomInfo):
        def get_danmu(self):
            if not select.select([self.danmuSocket], [], [], 1)[0]: return
            content = self.danmuSocket.pull()
            for msg in re.findall(b'({"type":.*?}})', content):
                try:
                    msg = json.loads(msg.decode('utf8', 'ignore'))
                    msg['NickName'] = msg.get('data', {}).get('from', {}
                        ).get('nickName', '')
                    msg['Content']  = msg.get('data', {}).get('content', '')
                    msg['MsgType']  = {'1': 'danmu', '206': 'gift'
                        }.get(msg['type'], 'other')
                except:
                    pass
                else:
                    self.danmuWaitTime = time.time() + self.maxNoDanMuWait
                    #self.msgPipe.append(msg)
                    if msg['MsgType'] == 'danmu':
                        self.countDanmuFn(msg['Content'])
        def heart_beat(self):
            self.danmuSocket.push(b'\x00\x06\x00\x00')
            time.sleep(60)
        return get_danmu, heart_beat
