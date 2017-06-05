import threading
from collections import namedtuple
import time
import os

import dl_analyse.record as record
from .rule import *

from .DouYu import DouYuDanMuClient
from .Panda import PandaDanMuClient


class DanmuCounter:
    def __init__(self, name):
        self.name = name
        self.DanmuList = []
        self.TripleSixList = []
        self.DouyuList = []
        self.LuckyList = []

    def count_danmu(self, content):
        if self.DanmuList:
            self.DanmuList[-1] += 1
            if any(word in content for word in Douyu_):
                self.DouyuList[-1] += 1
            if any(word in content for word in Lucky_):
                self.LuckyList[-1] += 1
            if any(word in content for word in Triple_):
                self.TripleSixList[-1] += 1

    def add_block(self):
        self.DanmuList.append(0)
        self.TripleSixList.append(0)
        self.DouyuList.append(0)
        self.LuckyList.append(0)

    def get_score(self, block_id=-1):
        return self.DouyuList[block_id] * ScoreRule_.douyu \
               + self.TripleSixList[block_id] * ScoreRule_.triple \
               + self.LuckyList[block_id] * ScoreRule_.lucky

    def get_count(self, block_id=-1):
        count_res = namedtuple("danmu", "triple", "douyu", "lucky")
        return count_res(self.DanmuList[block_id], self.TripleSixList[block_id], \
                         self.DouyuList[block_id], self.LuckyList[block_id])


class DanmuThread(threading.Thread):

    def __init__(self, room_id, platform, name):
        threading.Thread.__init__(self)
        self.__room_id      = room_id
        self.__name         = name
        self.__platform     = platform
        self.__deprecated   = False
        self.__baseClient   = None
        self.__client       = None
        self.__record_id    = ""
        self.danmuCounter = DanmuCounter(name)
        self.__url = 'http://' + PlatformUrl_[self.__name] + self.__room_id
        client_dict = {'panda': PandaDanMuClient,
                       'douyu': DouYuDanMuClient}
        if platform not in client_dict.keys():
            raise KeyError
        self.__baseClient = client_dict[platform]

    def room_is_live(self):
        return self.__client.get_live_status()

    def run(self, block_size=45):
        print("===========DanmuThread on {} starts===========".format(self.name))
        f = open('danmu_log', 'a')
        f.write("===========DanmuThread on {} starts===========\n".format(self.name))
        try:
            m = record.start_record(self.__room_id, block_size=ANALYSIS_DURATION_, \
                                    platform=self.__platform)
            f.write("m is {}\n".format(m))
            (record_id, start_time) = m
            start_time = int(start_time)
            self.__record_id = record_id
        except Exception as e:
            print(e)

            ONLINE_FLAGS[self.__room_id] = False
            print("{}'s starting has error and return".format(self.name))
            return
        statistic_filename = str(self.__room_id) + "_" + self.name + "_" + \
                             time.ctime(start_time) + ".csv"
        logdir = os.path.expanduser(LOGFILEDIR)
        block_id = 0
        logfile = open(logdir + statistic_filename, 'w')
        logfile.write("time, block, danmu, 666, 学不来, 逗鱼时刻\n")
        while self.__deprecated:
            self.danmuCounter.add_block()
            block_start_time = int(time.time())  # For record
            block_end_time = start_time + ANALYSIS_DURATION_ * (block_id + 1)  # For calculating sleeping_time
            sleep_time = block_end_time - time.time()
            print('{}\'s wait time is :{}'.format(self.name, sleep_time))
            time.sleep(sleep_time)

            count_res = (self.danmuCounter.get_count())
            try:
                logfile.write("{},{},{},{},{},{}\n".format(block_start_time, block_id, *count_res))
                print("{}'s logfile: time:{}, block:{}, danmu:{}, 666:{}, gou:{}, douyu:{}, audition:{}"
                      .format(self.name, block_start_time, block_id, *count_res))
                logfile.flush()
            except Exception as e:
                print(e)

            print('{}\'s current block_id is {}'.format(self.name, block_id))
            if block_id >= 3:
                if self.danmuCounter.DouyuList[block_id - 1] > 1:
                    l_count = self.danmuCounter.get_count(block_id - 1)
                    saved_video_name = '{}_douyu{}_block{}to{}_lucky{}_triple{}' \
                        .format(self.name, l_count.douyu, block_id - 3, block_id, l_count.lucky, l_count.triple)
                    threading.Thread(target=record.combine_block,
                                     args=(record_id, block_id - 3, block_id, saved_video_name)).start()
                elif self.danmuCounter.get_score(block_id - 1) >= ScoreThreshold_:
                    l_count = self.danmuCounter.get_count(block_id - 1)
                    saved_video_name = '{}_score{}_block{}to{}_douyu{}_triple{}_lucky{}' \
                        .format(self.name, self.danmuCounter.get_score(block_id - 1), l_count.douyu, block_id - 3,
                                block_id, l_count.douyu, l_count.triple, l_count.lucky)
                    threading.Thread(target=record.combine_block,
                                     args=(record_id, block_id - 3, block_id, saved_video_name)).start()

                # if douyu[-3] <= 1 and score_dict[-3] < THRESHOLD:
                    # save the clip but not combine it in case of use
                threading.Thread(target=record.delete_block, args=(record_id, block_id - 3, block_id - 3)).start()
            block_id += 1
        logfile.close()
        print("===========Thread on {} ends===========".format(self.name))
        f.write("===========DanmuThread on {} ends===========\n".format(self.name))
        f.close()

    def stop(self):
        self.__deprecated = True
        if self.__client:
            self.__client.deprecated = True
        record.stop_record(self.__record_id)