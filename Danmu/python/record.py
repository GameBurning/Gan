import requests

def start_record(roomid, platform='panda', block_size=30):
    para = {'room_id': roomid, 'platform': platform, 'output_config':{'block_size': block_size}}
    r = requests.post('http://127.0.0.1:5002/start', data=para)
    if r.status_code // 100 == 2:
        print(r.json())
        return((r.json()['info']['record_id'], r.json()['info']['start_time']))

    else:
        return (-1, -1)


def delete_block(record_id, start_id, end_id):
    print('delete block from {} to {}'.format(start_id, end_id))
    para = {'record_id': record_id, "start_block_id": start_id,\
            "end_block_id": end_id}
    r = requests.post('http://127.0.0.1:5002/delete', data = para)
    print(r.json()['info'])
    if r.json()['code'] == 0:
        return (-1, -1)
    else:
        print(r.json()['info'])
        return (start_id, end_id)


def combine_block(record_id, start_id, end_id, name):
    print('combine block from {} to {} into {}'.format(start_id, end_id, name))
    para = {'name':name, 'record_id':record_id, 'start_block_id':start_id,
            'end_block_id': end_id, 'start_block_offset': -1, \
            "end_block_offset": -1}
    r = requests.post('http://127.0.0.1:5002/process', data = para)
    print(r.json()['info'])
    if r.json()['code'] == 0:
        return (-1, -1)
    else:
        print(r.json()['info'])
        return (start_id, end_id)


if __name__ == "__main__":
    print(start_record(10455))
