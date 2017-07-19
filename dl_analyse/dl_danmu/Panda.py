import time, sys, re, json
import socket, select
import platform
from struct import pack

from .Abstract import AbstractDanMuClient

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


class PandaDanMuClient(AbstractDanMuClient):

    def get_live_status(self):
        try:
            j = requests.get('http://room.api.m.panda.tv/index.php?method=room.shareapi&roomid='
                             + str(self.roomID), timeout=5).json()
        except:
            self.logger.error(self.name + " timeout")
            return False
        try:
            return j['data']['roominfo']['status'] == '2'
        except json.decoder.JSONDecodeError as e:
            self.logger.critical("Inside Panda get_live Function: {}. Json is {}".format(e, j))
            return False
        except Exception as e:
            self.logger.critical("Inside Panda get_live Function:{}. Json is {}".format(e, j))

    def _prepare_env(self):
        trial = 0
        serverInfo = ""
        while trial < 5:
            try:
                roomId = self.roomID
                url = 'http://riven.panda.tv/chatroom/getinfo?roomid=%s'%(roomId)
                roomInfo = requests.get(url, timeout=5).json()
                self.logger.debug(roomInfo)
                url = 'http://api.homer.panda.tv/chatroom/getinfo'

                params = {
                    'rid': roomInfo['data']['rid'],
                    'roomid': roomId,
                    'retry': 0,
                    'sign': roomInfo['data']['sign'],
                    'ts': roomInfo['data']['ts'],
                    '_': int(time.time()), }
                serverInfo = requests.get(url, params).json()['data']
                serverAddress = serverInfo['chat_addr_list'][0].split(':')
                print("after prepare_env:", (serverAddress[0], int(serverAddress[1])), serverInfo)
                return (serverAddress[0], int(serverAddress[1])), serverInfo
            except Exception as e:
                self.logger.critical("prepare_env Exception: {} and serverInfo: {}".format(e, serverInfo))
                time.sleep(10)
            finally:
                trial += 1
        self.logger.critical("prepare danmu env failed")

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
                    msg['Content']  = msg.get('data', {}).get('content', '')
                    msg['MsgType'] = {'1': 'danmu', '206': 'gift'}.get(msg['type'], 'other')
                except Exception as e:
                    self.logger.error(e)
                    pass
                else:
                    self.danmuWaitTime = time.time() + self.maxNoDanMuWait
                    if msg['MsgType'] == 'danmu':
                        self.logger.debug(msg['Content'])
                        self.countDanmuFn(msg['Content'])
        def heart_beat(self):
            self.danmuSocket.push(b'\x00\x06\x00\x06')
            time.sleep(60)
        return get_danmu, heart_beat