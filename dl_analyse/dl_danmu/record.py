import requests
import time


def start_record(roomid, platform='panda', block_size=30, port=5002):
    f = open('danmu_log', 'a')
    f.write('get start command from {} and now requesting it to video server'.format(roomid))
    para = {'room_id': roomid, 'platform': platform, 'output_config':'{"block_size":' + str(block_size) + '}'}
    r = requests.post('http://127.0.0.1:{}/start'.format(port), data=para)

    f.write('{}: {}\n'.format(time.ctime(time.time())), r.json())
    f.close()
    if r.json()['code'] == 0:
        print(r.json())
        return r.json()['info']['record_id'], r.json()['info']['start_time']
    else:
        print(r.json()['info'])
        return -1, -1


def stop_record(record_id, port=5002):
    f = open('danmu_log', 'a')
    f.write('get start command from {} and now requesting it to video server'.format(record_id))
    r = requests.post('http://127.0.0.1:{}/stop'.format(port), data={"record_id": record_id})
    f.write('{}: {}\n'.format(time.ctime(time.time())), r.json())
    f.close()
    if r.json()['code'] == 0:
        print("{} stop succeeds".format(record_id))
        return True
    else:
        print(r.json()['info'])
        return False


def delete_block(record_id, start_id, end_id, port=5002):
    f = open('danmu_log', 'a')
    f.write('get delete command from {} and now requesting it to video server'.format(record_id))
    print('delete block from {} to {}'.format(start_id, end_id))
    para = {'record_id': record_id, "start_block_id": start_id,\
            "end_block_id": end_id}
    r = requests.post('http://127.0.0.1:5002/delete'.format(port), data = para)
    f.write('{}: {}\n'.format(time.ctime(time.time())), r.json())
    f.close()
    print(r.json()['info'])
    if r.json()['code'] == 0:
        print("delete successful")
        return True
    else:
        print(r.json()['info'])
        return False


def combine_block(record_id, start_id, end_id, name, port=5002):
    f = open('danmu_log', 'a')
    f.write('get combine command from {} and now requesting it to video server'.format(record_id))
    print('combine block from {} to {} into {}'.format(start_id, end_id, name))
    para = {'name':name, 'record_id':record_id, 'start_block_id': start_id,
            'end_block_id': end_id, 'start_block_offset': 0,\
            "end_block_offset": -1}
    r = requests.post('http://127.0.0.1:{}/process'.format(port), data=para)
    f.write('{}: {}\n'.format(time.ctime(time.time())), r.json())
    f.close()
    print(r.json()['info'])
    if r.json()['code'] == 0:
        print("{}'s combination succeed".format(name))
        return True
    else:
        print(r.json()['info'])
        return False


if __name__ == "__main__":
    print(start_record(10455))
