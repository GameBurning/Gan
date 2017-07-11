#!/usr/bin/env python3
from dl_danmu import DanmuThread
import argparse
import logging

INIT_PROPERTIES = 'init.properties'


parser = argparse.ArgumentParser()
parser.add_argument("-d", "--douyu", help="run for douyu",
                    action="store_true")
parser.add_argument("-p", "--panda", help="run for panda",
                    action="store_true")
args = parser.parse_args()


def load_init() -> []:
    room_info_list = []
    with open(INIT_PROPERTIES, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines:
            l_info_dict = {}
            for info in line.split():
                l_info_dict[info.split(':')[0].strip()] = info.split(':')[1].strip()
            if not args.douyu and not args.panda:
                print("Should append -d or -p")
                exit()
            if args.douyu and l_info_dict["platform"] == "douyu":
                room_info_list.append(l_info_dict)
            if args.panda and l_info_dict["platform"] == "panda":
                room_info_list.append(l_info_dict)
    return room_info_list


def main():
    room_info_list = load_init()
    for room in room_info_list:
        logger = logging.getLogger(room['abbr'])
        logger.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch_formatter = logging.Formatter('%(asctime)s %(name)s %(message)s')
        ch.setFormatter(ch_formatter)
        logger.addHandler(ch)
        room_thread = DanmuThread(room_id=room["id"], platform=room['platform'], name=room['name'], abbr=room['abbr'],
                                  factor=float(room['factor']), logger=logger)
        room_thread.start()

main()
