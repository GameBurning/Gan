import requests

def start_record(roomid, platform='panda', block_size = 30):
    para = {'room_id': roomid, 'platform': platform, 'output_config':'{"block_size":' + str(block_size) + '}'}
    r = requests.post('http://127.0.0.1:5002/start', data=para)
    if r.json()['code'] == 0:
        print(r.json())
        return ((r.json()['info']['record_id'], r.json()['info']['start_time']))
    else:
        print(r.json()['info'])
        return (-1, -1)


def stop_record(record_id):
    r = requests.post('http://127.0.0.1:5002/stop', data={"record_id": record_id})
    if r.json()['code'] == 0:
        print("{} stop succeeds".format(record_id))
        return True
    else:
        print(r.json()['info'])
        return False


def delete_block(record_id, start_id, end_id):
    print('delete block from {} to {}'.format(start_id, end_id))
    para = {'record_id': record_id, "start_block_id": start_id,\
            "end_block_id": end_id}
    r = requests.post('http://127.0.0.1:5002/delete', data = para)
    print(r.json()['info'])
    if r.json()['code'] == 0:
        print("delete successful")
        return (start_id, end_id)
    else:
        print(r.json()['info'])
        return (-1, -1)


def combine_block(record_id, start_id, end_id, name):
    print('combine block from {} to {} into {}'.format(start_id, end_id, name))
    para = {'name':name, 'record_id':record_id, 'start_block_id':start_id,
            'end_block_id': end_id, 'start_block_offset': -1, \
            "end_block_offset": -1}
    r = requests.post('http://127.0.0.1:5002/process', data = para)
    print(r.json()['info'])
    if r.json()['code'] == 0:
        print("{}'s combination succeed".format(name))
        return (start_id, end_id)
    else:
        print(r.json()['info'])
        return (-1, -1)
        
        
if __name__ == "__main__":
    print(start_record(10455))
