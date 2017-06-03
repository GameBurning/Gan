#!/usr/bin/env python3
import os
import threading
import time

import dl_analyse.record as record

from .dl_danmu.DouYu import DouYuDanMuClient
from .dl_danmu.Panda import PandaDanMuClient
from .dl_danmu.config import VERSION
from .rule import *
# from dl_analyse.dl_danmu import DanMuClient
# import record
# from dl_danmu import DanMuClient

__version__ = VERSION

DANMU_DICT = {}
TRIPLE_SIX_DICT = {}
LUCKY_DICT = {}
AUDITION_DICT = {}
DOUYU_DICT = {}
ONLINE_FLAGS = {}
RECORD_ID_DICT = {}
ANALYSIS_DURATION = 45
THRESHOLD = 800
MAIN_THREAD_SLEEP_TIME = 5


class DanmuCounter:
    def __init__(self):
        self.__DanmuList = []
        self.__TripleSixList = []
        self.__DouyuList = []
        self.__LuckyList = []

    def add_danmu(self, content):
        self.__DanmuList[-1] += 1
        if any(word in content for word in Douyu_):
            self.__DouyuList[-1] += 1
        if any(word in content for word in Lucky_):
            self.__LuckyList[-1] += 1
        if any(word in content for word in Triple_):
            self.__TripleSixList += 1

    def add_block(self):
        self.__DanmuList.append(0)
        self.__TripleSixList.append(0)
        self.__DouyuList.append(0)
        self.__LuckyList.append(0)

class DanmuThread(threading.Thread):

    def __init__(self, room_id, platform, name, url):
        threading.Thread.__init__(self)
        self.__room_id      = room_id
        self.__name         = name
        self.__url          = url
        self.__platform     = platform
        self.__functionDict = {'default': lambda x: 0}
        self.__isRunning    = False
        self.__baseClient   = None
        self.__client       = None
        self.danmuCounter = DanmuCounter()
        if 'http://' == url[:7]:
            self.__url = url
        else:
            self.__url = 'http://' + url
        client_dict = {'panda': PandaDanMuClient,
                       'douyu': DouYuDanMuClient}
        if not platform in client_dict.keys():
            raise KeyError
        self.__baseClient = client_dict[platform]

    def __register(self, fn, msgType):
        if fn is None:
            if msgType == 'default':
                self.__functionDict['default'] = lambda x: 0
            elif self.__functionDict.get(msgType):
                del self.__functionDict[msgType]
        else:
            self.__functionDict[msgType] = fn

    def default(self, fn):
        self.__register(fn, 'default')
        return fn

    def danmu(self, fn):
        self.__register(fn, 'danmu')
        return fn

    def gift(self, fn):
        self.__register(fn, 'gift')
        return fn

    def other(self, fn):
        self.__register(fn, 'other')
        return fn

    def start(self, block_size=45):
        print("===========DanmuThread on {} starts===========".format(self.name))
        f = open('danmu_log', 'a')
        f.write("===========DanmuThread on {} starts===========\n".format(self.name))
        try:
            m = record.start_record(self.__roomID, block_size=ANALYSIS_DURATION)
            f.write("m is {}\n".format(m))
            (record_id, start_time) = m
            start_time = int(start_time)
        except Exception as e:
            print(e)
            ONLINE_FLAGS[self.__roomID] = False
            print("{}'s starting has error and return".format(self.name))
            return
        RECORD_ID_DICT[self.__roomID] = record_id
        statistic_filename = str(self.__roomID) + "_" + self.name + "_" + \
                             time.ctime(start_time) + ".csv"
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
        while ONLINE_FLAGS[self.__roomID]:
            block_start_time = int(time.time())
            DANMU_DICT[self.__roomID] = 0
            TRIPLE_SIX_DICT[self.__roomID] = 0
            LUCKY_DICT[self.__roomID] = 0
            DOUYU_DICT[self.__roomID] = 0

            sleep_time = start_time + ANALYSIS_DURATION * (block_id + 1) - time.time()
            print('{}\'s wait time is :{}'.format(self.name, sleep_time))
            time.sleep(sleep_time)
            danmu.append(DANMU_DICT[self.__roomID])
            lucky.append(LUCKY_DICT[self.__roomID])
            douyu.append(DOUYU_DICT[self.__roomID])
            triple_six.append(TRIPLE_SIX_DICT[self.__roomID])
            audition.append(AUDITION_DICT[self.__roomID])

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

    def stop(self):
        self.__isRunning = False
        if self.__client:
            self.__client.deprecated = True


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
            # online_status = room_is_online(id, name)
            # if not ONLINE_FLAGS[id] and online_status:
            #     danmulog_filename = str(id) + "_" + name + "_Danmu" + ".txt"
            #     logdir = os.path.expanduser(LOGFILEDIR)
            #     f = open(logdir + danmulog_filename, 'a')
            #     ONLINE_FLAGS[id] = True
            #     threading.Thread(target=getChatInfo, args=(id, name, f)).start()
            #     DanmuThread(id, name).start()
            #     print("{} goes online".format(name))
            #     f.write("{} goes online\n".format(name))
            # elif ONLINE_FLAGS[id] and not online_status:
            #     if RECORD_ID_DICT.get(id, None) is not None:
            #         stop_success = record.stop_record(RECORD_ID_DICT[id])
            #         if stop_success is False:
            #             continue
            #         RECORD_ID_DICT[id] = None
            #     ONLINE_FLAGS[id] = False
            #     print("{} goes offline".format(name))
            #     f.write("{} goes offline\n".format(name))
            pass
        time.sleep(MAIN_THREAD_SLEEP_TIME)
        f.flush()


if __name__ == '__main__':
    main()
