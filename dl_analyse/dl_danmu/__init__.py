# -*- coding: utf-8 -*-
import os
import threading
import time
import logging

from .record import Recorder
from .DouYu import DouYuDanMuClient
from .Panda import PandaDanMuClient
from .Zhanqi import ZhanQiDanMuClient
from .rule import *
from .DanmuCounter import DanmuCounter


class DanmuThread(threading.Thread):

    def __init__(self, room_id, platform, name, abbr, factor, logger, block_size = Block_Size_In_Second_,
                 live_status_rescan_interval=30):
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
        self.__factor       = factor
        self.__live_status_rescan_interval = live_status_rescan_interval
        self.__block_size   = block_size
        self.__dc           = DanmuCounter(name)
        self.__url          = 'http://' + PlatformUrl_[self.__platform] + self.__room_id
        client_dict = {'panda': PandaDanMuClient,
                       'douyu': DouYuDanMuClient,
                       'zhanqi': ZhanQiDanMuClient}
        self.logger = logger
        if platform not in client_dict.keys():
            raise KeyError
        self.__baseClient   = client_dict[platform]
        self.__client = self.__baseClient(self.__room_id, self.__name, self.__dc.count_danmu, self.logger)
        self.__recorder    = Recorder(self.__name, self.logger)

    def room_is_live(self):
        return self.__client.get_live_status()

    def run(self):
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
        # Log method for csv
        def _log(_content, _file):
            print(self.__name + ", " + _content)
            _file.write(time.ctime(time.time()) + ": " + self.__name + ", " + _content + "\n")
            _file.flush()

        # Danmu Thread On
        self.logger.info("===========DanmuThread of {} starts===========".format(self.__name))

        # Start recording
        try:
            if Record_Mode_:
                trial_counter = 0
                while trial_counter < 5:
                    m = self.__recorder.start_record(roomid=self.__room_id, block_size=self.__block_size,
                                            platform=self.__platform)
                    (record_id, start_time) = m
                    if start_time != -1:
                        start_time = int(start_time)
                        self.__record_id = record_id

                        debug_file_path = self.get_record_folder() + 'danmu_log_{}'.format(self.__record_id)
                        fh = logging.FileHandler(filename=debug_file_path)
                        fh.setLevel(logging.INFO)
                        fh_formatter = logging.Formatter('%(asctime)s %(message)s', datefmt='%m/%d %I:%M:%S')
                        fh.setFormatter(fh_formatter)
                        self.logger.addHandler(fh)
                        self.__recorder.logger.addHandler(fh)
                        self.__client.logger.addHandler(fh)
                        self.logger.info("start_record of {} feedback: {}".format(self.__name, m))
                        break
                    else:
                        self.logger.info("start_record of {} failed: {}".format(self.__name, m))
                        time.sleep(5)
                        trial_counter += 1
                else:
                    return
            else:
                start_time = int(time.time())
        except Exception as e:
            print("Exception at starting period: {}".format( e))
            self.__is_running = False
            print("Starting has error and return")
            return
        self.logger.info("===========Successfully start recording===========")
        self.__client.deprecated = False
        threading.Thread(target=self.__client.start).start()

        # Recording starts and now is block 0
        self.__is_running = True
        counter_filename = self.__name + "_" + self.__record_id + ".csv"
        block_id = 0
        counter_file = open(self.get_record_folder() + counter_filename, 'w')
        counter_file.write("block, danmu, 666, 学不来, 逗鱼时刻\n")
        l_last_block_data = (False, "", (0, 0), (0, 0, 0, 0))  # (is_processed, old_name, (block), (d,s,t,l))

        # Not stopped by outer part
        while not self.__should_stop:
            self.__dc.add_block()
            block_end_time = start_time + self.__block_size * (block_id + 1)  # For calculating sleeping_time
            sleep_time = block_end_time - time.time()
            time.sleep(sleep_time)

            if not os.path.isfile(self.get_record_folder() + str(block_id) + '.flv'):
                self.logger.error("No recording file {}, exit".format(self.get_record_folder() + str(block_id) + '.flv'))
                break

            count_res = (self.__dc.get_count())
            try:
                counter_file.write("{},{},{},{},{}\n".format(block_id, *count_res))
                counter_file.flush()
                self.logger.info("logfile: block:{}, danmu:{}, 666:{}, gou:{}, douyu:{}".
                     format(block_id, *count_res))
                # counter_file.flush()
            except Exception as e:
                self.logger.critical("Except inside while loop in gan: {}. Counter is {}".format(e, count_res))

            try:
                if Record_Mode_ and block_id >= 3:
                    self.logger.debug("{} has {} douyu times and target number is {}".
                         format(self.__name, sum(i >= 2 for i in self.__dc.DouyuList),
                                self.__dc.DouyuList[block_id - 1]))
                    if self.__dc.DouyuList[-2] * self.__factor > 8 or self.__dc.LuckyList[-2] * self.__factor > 100:
                        if l_last_block_data[0]:
                            l_c = self.__dc.get_count(-2)
                            l_pot = max((l_c.douyu + l_last_block_data[3][0]) * self.__factor / 40,
                                      self.__dc.LuckyList[-2] * self.__factor / 700)
                            l_video_name = '{}_pos:{:.2f}_from:{}_to:{}'\
                                .format(self.__abbr, l_pot,
                                       l_last_block_data[2][0], block_id)

                            self.logger.info('{} should append {} to {}'.format(self.__name, l_last_block_data[2][0],
                                                                                block_id))
                            threading.Thread(target=self.__recorder.append_block,
                                             args=(block_id, l_last_block_data[1],
                                                   l_video_name)).start()
                            l_last_block_data = (True, l_video_name, (l_last_block_data[2][0], block_id),
                                                 (l_last_block_data[3][0] + l_c.douyu,
                                                  l_last_block_data[3][1] + self.__dc.get_score(-2),
                                                  l_last_block_data[3][2] + l_c.triple,
                                                  l_last_block_data[3][3] + l_c.lucky))
                        else:
                            l_c = self.__dc.get_count(-2)
                            l_pot = max(l_c.douyu * self.__factor / 30, self.__dc.LuckyList[-2] * self.__factor / 500)
                            l_video_name = '{}_pos:{:.2f}_from:{}_to:{}'\
                                .format(self.__abbr, l_pot, block_id - 3, block_id)
                            l_last_block_data = (True, l_video_name, (block_id - 3, block_id),
                                                 (l_c.douyu, self.__dc.get_score(-2), l_c.triple, l_c.lucky))
                            print('work here 6')
                            self.logger.info('{} should combine {} to {}'.format(self.__name, block_id - 3, block_id))
                            threading.Thread(target=self.__recorder.combine_block,
                                             args=(block_id - 3, block_id,
                                                   l_video_name)).start()
                    else:
                        l_last_block_data = (False, "")
                    threading.Thread(target=self.__recorder.delete_block, args=(block_id - 3, block_id - 3)).start()
            except Exception as e:
                self.logger.critical("In record has Exception {}".format(e))
            self.logger.info("last_block_data is {}".format(l_last_block_data))
            block_id += 1

        self.__is_running = False
        self.__dc.reset()
        if self.__client:
            self.__client.deprecated = True
        counter_file.close()
        self.logger.info("===========DanmuThread of {} ends===========".format(self.__name))
        self.__recorder.stop_record()

