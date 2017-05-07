import requests
import json

def start_record(roomid, platform='panda', block_size=30):
    para = {'room_id': roomid, 'platform': platform, 'output_config': \
        json.dumps({'block_size': block_size})}
    r = requests.post('http://127.0.0.1:5002/start', data=para)
    print(r.json())
    return(r.json()['start_time'])


if __name__ == "__main__":
    print(start_record(10455))
