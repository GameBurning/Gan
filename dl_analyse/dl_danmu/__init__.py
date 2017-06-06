import os
import threading
import time

import dl_danmu.record as record
from .DouYu import DouYuDanMuClient
from .Panda import PandaDanMuClient
from .rule import *
from json.decoder import JSONDecodeError


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
        CountRes = namedtuple("CountRes", ["danmu", "triple", "douyu", "lucky"])

        return CountRes(self.DanmuList[block_id], self.TripleSixList[block_id],
                         self.DouyuList[block_id], self.LuckyList[block_id])


class DanmuThread(threading.Thread):

    def __init__(self, room_id, platform, name, live_status_rescan_interval=30):
        threading.Thread.__init__(self)
        self.__room_id      = room_id
        self.__name         = name
        self.__platform     = platform
        self.__is_live      = False
        self.__is_running   = False
        self.__should_stop  = False
        self.__baseClient   = None
        self.__client       = None
        self.__record_id    = ""
        self.__live_status_rescan_interval = live_status_rescan_interval
        self.danmuCounter = DanmuCounter(name)
        self.__url = 'http://' + PlatformUrl_[self.__platform] + self.__room_id
        client_dict = {'panda': PandaDanMuClient,
                       'douyu': DouYuDanMuClient}
        if platform not in client_dict.keys():
            raise KeyError
        self.__baseClient = client_dict[platform]
        self.__client = self.__baseClient(self.__room_id, self.__name, self.danmuCounter.count_danmu)

    def room_is_live(self):
        return self.__client.get_live_status()

    def run(self, block_size=45):
        while True:
            l_live_status = self.room_is_live()
            if self.__is_running and not l_live_status:
                self.stop()
            elif not self.__is_running and l_live_status:
                self.gan()
            time.sleep(self.__live_status_rescan_interval)

    def stop(self):
        if self.__client:
            self.__client.deprecated = True
        if Record_Mode_:
            record.stop_record(self.__record_id)
        self.__should_stop = True

    def gan(self):
        print("===========DanmuThread on {} starts===========".format(self.__name))
        f = open('danmu_log', 'a')
        f.write("===========DanmuThread on {} starts===========\n".format(self.__name))
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
            print("{}'s starting has error and return".format(self.__name))
            return
        receive_thread = threading.Thread(target=self.__client.start)
        receive_thread.start()
        self.__is_running = True
        statistic_filename = str(self.__room_id) + "_" + self.name + "_" + time.ctime(start_time) + ".csv"
        log_dir = os.path.expanduser(LogFilePath_)
        block_id = 0
        logfile = open(log_dir + statistic_filename, 'w')
        logfile.write("time, block, danmu, 666, 学不来, 逗鱼时刻\n")
        while not self.__should_stop:
            self.danmuCounter.add_block()
            block_start_time = int(time.time())  # For record
            block_end_time = start_time + Block_Size_In_Second_ * (block_id + 1)  # For calculating sleeping_time
            sleep_time = block_end_time - time.time()
            # print('{}\'s wait time is :{}'.format(self.__name, sleep_time))
            time.sleep(sleep_time)

            count_res = (self.danmuCounter.get_count())
            try:
                logfile.write("{},{},{},{},{},{}\n".format(block_start_time, block_id, *count_res))
                print("{}'s logfile: time:{}, block:{}, danmu:{}, 666:{}, gou:{}, douyu:{}"
                      .format(self.__name, block_start_time, block_id, *count_res))
                logfile.flush()
            except Exception as e:
                print("inside while loop in gan: {}".format(e))

            # print('{}\'s current block_id is {}'.format(self.__name, block_id))

            if Record_Mode_ and block_id >= 3:
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

                threading.Thread(target=record.delete_block, args=(record_id, block_id - 3, block_id - 3)).start()
            block_id += 1
        self.__is_running = False
        logfile.close()
        print("===========Thread on {} ends===========".format(self.__name))
        f.write("===========DanmuThread on {} ends===========\n".format(self.__name))
        f.close()
