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
#import danmu.python.record as record
#from analyse.dl_danmu import DanMuClient
import record
from dl_danmu import DanMuClient

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
RECORD_ID_DICT = {}
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
        f = open('danmu_log', 'a')
        f.write("===========DanmuThread on {} starts===========\n".format(self.name))
        try:
            m = record.start_record(self.roomID, block_size=ANALYSIS_DURATION)
            f.write("m is {}\n".format(m))
            (record_id, start_time) = m
            start_time = int(start_time)
        except Exception as e:
            print(e)
            ONLINE_FLAGS[self.roomID] = False
            print("{}'s starting has error and return".format(self.name))
            return
        RECORD_ID_DICT[self.roomID] = record_id
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
                if douyu[-3] <= 1 and score_dict[-3] < THRESHOLD:
                    # save the clip but not combine it in case of use
                    threading.Thread(target=record.delete_block, args=(record_id, block_id - 3,
                                                                   block_id - 3)).start()
            block_id += 1
        logfile.close()
        print("===========Thread on {} ends===========".format(self.name))
        f.write("===========DanmuThread on {} ends===========\n".format(self.name))
        f.close()


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


def main():
    roomInfos = loadInit()
    f = open('danmu_log','w')
    f.write('Log start\n')
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
                f.write("{} goes online\n".format(name))
            elif ONLINE_FLAGS[id] and not online_status:
                if RECORD_ID_DICT.get(id, None) is not None:
                    stop_success = record.stop_record(RECORD_ID_DICT[id])
                    if stop_success is False:
                        continue
                    RECORD_ID_DICT[id] = None
                ONLINE_FLAGS[id] = False
                print("{} goes offline".format(name))
                f.write("{} goes offline\n".format(name))
        time.sleep(MAIN_THREAD_SLEEP_TIME)
        f.flush()


if __name__ == '__main__':
    main()
