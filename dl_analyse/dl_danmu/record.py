import requests
import time


def start_record(roomid, platform='panda', block_size=45, port=5002):
    f = open('danmu_log', 'a')
    f.write('get start command from {} and now requesting it to video server\n'.format(roomid))
    para = {'room_id': roomid, 'platform': platform, 'output_config':'{"block_size":' + str(block_size) + '}'}
    r = requests.post('http://127.0.0.1:{}/start'.format(port), data=para)

    f.write('{}: {}\n'.format(time.ctime(time.time()), r.json()))

    if r.json()['code'] == 0:
        print("{}'s start succeed and json info is {}".format(roomid, r.json()['info']))
        f.write("{}'s start succeed and json info is {}\n".format(roomid, r.json()['info']))
        return r.json()['info']['record_id'], r.json()['info']['start_time']
    else:
        print("{}'s start failed and json info is {}".format(roomid, r.json()['info']))
        f.write("{}'s start failed and json info is {}\n".format(roomid, r.json()['info']))
        return -1, -1
    f.close()


def stop_record(record_id, port=5002):
    f = open('danmu_log', 'a')
    f.write('get stop command from {} and now requesting it to video server'.format(record_id))
    r = requests.post('http://127.0.0.1:{}/stop'.format(port), data={"record_id": record_id})
    f.write('{}: {}\n'.format(time.ctime(time.time()), r.json()))
    if r.json()['code'] == 0:
        print("{} stop succeeds and json info is {}".format(record_id, r.json()['info']))
        f.write("{} stop succeeds and json info is {}\n".format(record_id, r.json()['info']))
        return True
    else:
        print("{} stop failed and json info is {}".format(record_id, r.json()['info']))
        f.write("{} stop failed and json info is {}\n".format(record_id, r.json()['info']))
        return False
    f.close()


def delete_block(record_id, start_id, end_id, port=5002):
    f = open('danmu_log', 'a')
    f.write('get delete command from {} to delete {} to {} and now requesting it to video server'.format(record_id,
                                                                                                         start_id,
                                                                                                         end_id))
    print('delete block from {} to {}'.format(start_id, end_id))
    para = {'record_id': record_id, "start_block_id": start_id,\
            "end_block_id": end_id}
    r = requests.post('http://127.0.0.1:5002/delete'.format(port), data=para)
    f.write('{}: {}\n'.format(time.ctime(time.time()), r.json()))

    if r.json()['code'] == 0:
        print("{}'s delete succeed and json info is {}\n".format(record_id, r.json()['info']))
        f.write("{}'s delete succeed and json info is {}\n".format(record_id, r.json()['info']))
        return True
    else:
        print("{}'s delete failed and json info is {}\n".format(record_id, r.json()['info']))
        f.write("{}'s delete failed and json info is {}\n".format(record_id, r.json()['info']))
        return False
    f.close()


def combine_block(record_id, start_id, end_id, name, port=5002):
    f = open('danmu_log', 'a')
    f.write('get combine command from {} to combine {} to {} and now requesting it to video server\n'.format(record_id,
                                                                                                           start_id,
                                                                                                           end_id))
    print('combine block from {} to {} into {}'.format(start_id, end_id, name))
    para = {'name':name, 'record_id':record_id, 'start_block_id': start_id,
            'end_block_id': end_id, 'start_block_offset': 0,\
            "end_block_offset": -1}
    r = requests.post('http://127.0.0.1:{}/process'.format(port), data=para)
    f.write('{}: {}\n'.format(time.ctime(time.time()), r.json()))
    if r.json()['code'] == 0:
        print("{}'s({}) combination succeed and json info is {}\n".format(name, record_id, r.json()['info']))
        f.write("{}'s({}) combination succeed and json info is {}\n".format(name, record_id, r.json()['info']))
        return True
    else:
        print("{}'s({}) combination failed and json info is {}\n".format(name, record_id, r.json()['info']))
        f.write("{}'s({}) combination failed and json info is {}\n".format(name, record_id, r.json()['info']))
        return False
    f.close()


def append_block(record_id, block_id, old_name, new_name, port=5002):
    f = open('danmu_log', 'a')
    f.write('get append request to append append_id {} to old_name {}').__format__(block_id, old_name)
    print('append block from {} to {}').format(block_id, old_name)
    para = {'name': old_name, 'new_name': new_name, 'block_id': block_id, 'record_id': record_id}
    r = requests.post('http://127.0.0.1:{}/append'.format(port), data=para)
    if r.json()['code'] == 0:
        print("{}'s append succeed and json info is {}\n".format(record_id, r.json()['info']))
        f.write("{}'s append succeed and json info is {}\n".format(record_id, r.json()['info']))
    else:
        print("{}'s append failed and json info is {}\n".format(record_id, r.json()['info']))
        f.write("{}'s append failed and json info is {}\n".format(record_id, r.json()['info']))
    f.close()

if __name__ == "__main__":
    print(start_record(10455))
