# -*- coding: utf-8 -*-
import os
import threading
import time

from . import record
from .DouYu import DouYuDanMuClient
from .Panda import PandaDanMuClient
from .Zhanqi import ZhanQiDanMuClient
from .rule import *
from .DanmuCounter import DanmuCounter


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
                       'douyu': DouYuDanMuClient,
                       'zhanqi': ZhanQiDanMuClient}
        if platform not in client_dict.keys():
            raise KeyError
        self.__baseClient = client_dict[platform]
        logfile_path = self.get_record_folder() + '{}_danmu_log'.format(self.__record_id)
        self.__client = self.__baseClient(self.__room_id, self.__name, self.__dc.count_danmu, logfile_path)

    def room_is_live(self):
        return self.__client.get_live_status()

    def run(self, block_size=45):
        while True:
            l_live_status = self.room_is_live()
            print('{} is alive? {}'.format(self.__name, l_live_status))
            if not self.__is_running and l_live_status:
                self.gan()
            time.sleep(self.__live_status_rescan_interval)

    def get_record_folder(self):
        _dir = os.path.expanduser(LogFilePath_)
        record_folder_dir = _dir + self.__record_id + '/'
        return record_folder_dir

    def gan(self):
        debug_file = open(self.get_record_folder() + '{}_danmu_log'.format(self.__record_id), 'a', encoding='utf-8')

        def _log(_content, _file=debug_file):
            print(self.__name + ", " + _content)
            if _file != debug_file:
                _file.write(_content + "\n")
            else:
                _file.write(time.ctime(time.time()) + ": " + self.__name + ", " + _content+"\n")
        # Danmu Thread On
        _log("===========DanmuThread starts===========")

        # Start recording
        try:
            if Record_Mode_:
                trial_counter = 0
                while trial_counter < 5:
                    m = record.start_record(self.__room_id, block_size=Block_Size_In_Second_, platform=self.__platform)
                    (record_id, start_time) = m
                    _log("start_record of {} feedback: {}".format(self.__name, m))
                    if start_time != -1:
                        start_time = int(start_time)
                        self.__record_id = record_id
                        break
                    else:
                        _log("{} can't get steam".format(self.__name))
                        time.sleep(5)
                        trial_counter += 1
                else:
                    return
            else:
                start_time = int(time.time())
        except Exception as e:
            _log("Exception at starting period: {}".format( e))
            self.__is_running = False
            _log("Starting has error and return")
            return
        _log("===========Successfully start recording===========")
        threading.Thread(target=self.__client.start).start()

        # Recording starts and now is block 0
        self.__is_running = True
        counter_filename = self.__name + "_" + self.__record_id + ".csv"
        block_id = 0
        counter_file = open(self.get_record_folder() + counter_filename, 'a')
        counter_file.write("time, block, danmu, 666, 学不来, 逗鱼时刻\n")
        l_last_block_data = (False, "", (0, 0), (0, 0, 0, 0)) # (is_processed, old_name, (block), (d,s,t,l))

        # Not stopped by outer part
        while not self.__should_stop:
            self.__dc.add_block()
            block_start_time = time.ctime(time.time())  # For record
            block_end_time = start_time + Block_Size_In_Second_ * (block_id + 1)  # For calculating sleeping_time
            sleep_time = block_end_time - time.time()
            # print('{}\'s wait time is :{}'.format(self.__name, sleep_time))
            time.sleep(sleep_time)

            if not os.path.isfile(self.get_record_folder() + str(block_id) + '.flv'):
                _log("No recording file {}, exit".format(self.get_record_folder() + str(block_id) + '.flv'))
                break

            count_res = (self.__dc.get_count())
            try:
                _log("{},{},{},{},{},{}\n".format(block_start_time, block_id, *count_res), counter_file)
                _log("logfile: time:{}, block:{}, danmu:{}, 666:{}, gou:{}, douyu:{}".
                     format(block_start_time, block_id, *count_res))
                counter_file.flush()
            except Exception as e:
                _log("inside while loop in gan: {}".format(e))

            try:
                if Record_Mode_ and block_id >= 3:
                    _log("has {} douyu times and target number is {}".
                         format(sum(i >= 2 for i in self.__dc.DouyuList),
                                self.__dc.DouyuList[block_id - 1]))
                    if self.__dc.get_score(-2) >= ScoreThreshold_ or self.__dc.DouyuList[-2] > 2:
                        if l_last_block_data[0]:
                            l_c = self.__dc.get_count(-2)
                            l_video_name = '{}_d{}_b{}to{}_s{}_t{}_l{}'.\
                                format(self.__abbr, l_c.douyu + l_last_block_data[3][0], l_last_block_data[2][0],
                                       block_id, self.__dc.get_score(-2)+l_last_block_data[3][1],
                                       l_last_block_data[3][2] + l_c.triple, l_last_block_data[3][3] + l_c.lucky)
                            _log('should append {} to {}'.format(block_id, l_last_block_data[1]))
                            threading.Thread(target=record.append_block,
                                             args=(self.__record_id, block_id, l_last_block_data[1],
                                                   l_video_name)).start()
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
                            _log('should combine {} to {}'.format(block_id - 3, block_id))
                            threading.Thread(target=record.combine_block,
                                             args=(self.__record_id, block_id - 3, block_id, l_video_name)).start()
                    else:
                        l_last_block_data = (False, "")
                    threading.Thread(target=record.delete_block, args=(self.__record_id, block_id - 3,
                                                                       block_id - 3)).start()
            except Exception as e:
                _log("In record has Exception {}".format(e))
            _log("last_block_data is {}".format(l_last_block_data))
            block_id += 1

        self.__is_running = False
        self.__dc.reset()
        if self.__client:
            self.__client.deprecated = True
        counter_file.close()
        _log("===========Thread ends===========")
        record.stop_record(self.__record_id)
        debug_file.close()
