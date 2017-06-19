# -*- coding: utf-8 -*-
import os
import threading
import time

from . import record
from .DouYu import DouYuDanMuClient
from .Panda import PandaDanMuClient
from .rule import *


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
        CountRes = namedtuple("CountRes", ["danmu", "triple", "lucky", "douyu"])

        return CountRes(self.DanmuList[block_id], self.TripleSixList[block_id],
                        self.LuckyList[block_id], self.DouyuList[block_id])


class DanmuThread(threading.Thread):

    def __init__(self, room_id, platform, name, abbr, live_status_rescan_interval=30):
        threading.Thread.__init__(self)
        self.__room_id      = room_id
        self.__name         = name
        self.__abbr         = abbr
        self.__platform     = platform
        self.__is_live      = False
        self.__is_running   = False
        self.__should_stop  = False
        self.__baseClient   = None
        self.__client       = None
        self.__record_id    = ""
        self.__live_status_rescan_interval = live_status_rescan_interval
        self.__dc = DanmuCounter(name)
        self.__url = 'http://' + PlatformUrl_[self.__platform] + self.__room_id
        client_dict = {'panda': PandaDanMuClient,
                       'douyu': DouYuDanMuClient}
        if platform not in client_dict.keys():
            raise KeyError
        self.__baseClient = client_dict[platform]
        self.__client = self.__baseClient(self.__room_id, self.__name, self.__dc.count_danmu)

    def room_is_live(self):
        return self.__client.get_live_status()

    def run(self, block_size=45):
        while True:
            l_live_status = self.room_is_live()
            print('{} is alive? {}'.format(self.__name, l_live_status))
            if not self.__is_running and l_live_status:
                self.gan()
            time.sleep(self.__live_status_rescan_interval)

    def gan(self):
        print("===========DanmuThread on {}({}) starts===========".format(self.__name, self.__room_id))
        f = open('danmu_log', 'a', encoding='utf-8')
        f.write("===========DanmuThread on {}({}) starts===========\n".format(self.__name, self.__room_id))
        try:
            if Record_Mode_:
                trial_counter = 0
                while trial_counter < 5:
                    m = record.start_record(self.__room_id, block_size=Block_Size_In_Second_, platform=self.__platform)
                    print(m)
                    (record_id, start_time) = m
                    f.write("m is {}\n".format(m))
                    if start_time != -1:
                        start_time = int(start_time)
                        self.__record_id = record_id
                        break
                    else:
                        print("{} can't get steam".format(self.__name))
                        time.sleep(5)
                        trial_counter += 1
                else:
                    return
            else:
                start_time = int(time.time())
        except Exception as e:
            print("inside gan {}".format(e))
            self.__is_running = False
            print("{}'s({}) starting has error and return".format(self.__name, self.__record_id))
            return
        f.write("===========record id of {} is {} starts===========\n".format(self.__name, self.__record_id))
        receive_thread = threading.Thread(target=self.__client.start)
        receive_thread.start()
        self.__is_running = True
        statistic_filename = str(self.__room_id) + "_" + self.__name + "_" + time.ctime(start_time) + ".csv"
        log_dir = os.path.expanduser(LogFilePath_)
        block_id = 0
        logfile = open(log_dir + self.__record_id + '/' + statistic_filename, 'w')
        logfile.write("time, block, danmu, 666, 学不来, 逗鱼时刻\n")
        l_last_block_data = (False, "", (0, 0), (0, 0, 0, 0)) # (is_processed, old_name, (block), (d,s,t,l))
        while not self.__should_stop:
            self.__dc.add_block()
            block_start_time = int(time.time())  # For record
            block_end_time = start_time + Block_Size_In_Second_ * (block_id + 1)  # For calculating sleeping_time
            sleep_time = block_end_time - time.time()
            # print('{}\'s wait time is :{}'.format(self.__name, sleep_time))
            time.sleep(sleep_time)

            if not os.path.isfile(log_dir + self.__record_id + '/' + str(block_id) + '.flv'):
                print("No recording file, exit")
                break

            count_res = (self.__dc.get_count())
            try:
                logfile.write("{},{},{},{},{},{}\n".format(block_start_time, block_id, *count_res))
                print("{}'s({}) logfile: time:{}, block:{}, danmu:{}, 666:{}, gou:{}, douyu:{}"
                      .format(self.__name, self.__record_id, block_start_time, block_id, *count_res))
                logfile.flush()
            except Exception as e:
                print("inside while loop in gan: {}".format(e))

            # print('{}\'s current block_id is {}'.format(self.__name, block_id))

            try:
                if Record_Mode_ and block_id >= 3:
                    print("{}'({}) has {} douyu times and target number is {}".
                          format(self.__name, self.__record_id, sum(i >= 2 for i in self.__dc.DouyuList),
                                 self.__dc.DouyuList[block_id - 1]))
                    if self.__dc.get_score(-2) >= ScoreThreshold_ or self.__dc.DouyuList[-2] > 2:
                        if l_last_block_data[0]:
                            l_c = self.__dc.get_count(-2)
                            l_video_name = '{}_d{}_b{}to{}_s{}_t{}_l{}'.\
                                format(self.__abbr, l_c.douyu + l_last_block_data[3][0], l_last_block_data[2][0],
                                       block_id, self.__dc.get_score(-2)+l_last_block_data[3][1],
                                       l_last_block_data[3][2] + l_c.triple, l_last_block_data[3][3] + l_c.lucky)
                            threading.Thread(target=record.append_block,
                                             args=(self.__record_id, block_id, l_last_block_data[1], l_video_name))
                            l_last_block_data = (True, l_video_name, (l_last_block_data[2][0], block_id),
                                             (l_last_block_data[3][0] + l_c.douyu,
                                              l_last_block_data[3][1] + self.__dc.get_score(-2),
                                              l_last_block_data[3][2] + l_c.triple,
                                              l_last_block_data[3][3] + l_c.lucky))
                        else:
                            l_c = self.__dc.get_count(-2)
                            l_video_name = '{}_d{}_b{}to{}_s{}_t{}_l{}' \
                                .format(self.__abbr, l_c.douyu, block_id - 3, block_id, self.__dc.get_score(-2),
                                        l_c.triple, l_c.lucky)
                            l_last_block_data = (True, l_video_name, (block_id - 3, block_id),
                                                 (l_c.douyu, self.__dc.get_score(-2), l_c.triple, l_c.lucky))
                            threading.Thread(target=record.combine_block,
                                             args=(self.__record_id, block_id - 3, block_id, l_video_name)).start()
                    else:
                        l_last_block_data = (False, "")
                    threading.Thread(target=record.delete_block, args=(self.__record_id, block_id - 3,
                                                                       block_id - 3)).start()
            except Exception as e:
                f.write("In record has Exception {}".format(e))

            block_id += 1
        self.__is_running = False
        if self.__client:
            self.__client.deprecated = True
        logfile.close()
        print("===========Thread on {} ends===========".format(self.__name))
        f.write("===========DanmuThread on {} ends===========\n".format(self.__name))
        f.close()
