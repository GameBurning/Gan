#!/usr/bin/env python3
from dl_danmu import DanmuThread
INIT_PROPERTIES = 'init.properties'


def load_init() -> []:
    room_info_list = []
    with open(INIT_PROPERTIES, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        for line in lines:
            l_info_dict = {}
            for info in line.split():
                l_info_dict[info.split(':')[0].strip()] = info.split(':')[1].strip()
            room_info_list.append(l_info_dict)
    return room_info_list


def main():
    room_info_list = load_init()
    for room in room_info_list:
        room_thread = DanmuThread(room_id=room["id"], platform=room['platform'], name=room['name'], abbr=room['abbr'])
        room_thread.start()

main()
