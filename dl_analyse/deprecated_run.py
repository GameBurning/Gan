#!/usr/bin/env python3
import time

from .dl_danmu.config import VERSION, INIT_PROPERTIES

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


MAIN_THREAD_SLEEP_TIME = 5


def load_init()->[]:
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
    roomInfos = load_init()
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
