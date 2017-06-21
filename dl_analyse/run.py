#!/usr/bin/env python3
from dl_danmu import DanmuThread
import argparse

INIT_PROPERTIES = 'init.properties'


parser = argparse.ArgumentParser()
parser.add_argument("-d", "--douyu", help="run douyu rooms",
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
            if args.douyu:
                if l_info_dict["platform"] == "douyu":
                    room_info_list.append(l_info_dict)
            else:
                if l_info_dict["platform"] != "douyu":
                    room_info_list.append(l_info_dict)
    return room_info_list


def main():
    room_info_list = load_init()
    for room in room_info_list:
        room_thread = DanmuThread(room_id=room["id"], platform=room['platform'], name=room['name'], abbr=room['abbr'])
        room_thread.start()

main()
