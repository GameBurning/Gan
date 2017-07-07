import requests
import time


def _log(_content, _file):
    print(_content)
    _file.write(time.ctime(time.time()) + ": " + _content + '\n')


def start_record(roomid, platform='panda', block_size=45, port=5002):
    with open("starting_log", 'a') as f:
        _log('get start command from {} and now requesting it to video server\n'.format(roomid), f)
        para = {'room_id': roomid, 'platform': platform, 'output_config':'{"block_size":' + str(block_size) + '}'}
        r = requests.post('http://127.0.0.1:{}/start'.format(port), data=para)

        _log('{}: {}\n'.format(time.ctime(time.time()), r.json()), f)

        if r.json()['code'] == 0:
            _log("{}'s start succeed and json info is {}".format(roomid, r.json()['info']), f)
            return r.json()['info']['record_id'], r.json()['info']['start_time']
        else:
            _log("{}'s start failed and json info is {}".format(roomid, r.json()['info']), f)
            return -1, -1


def stop_record(record_id, logfile_path, port=5002):
    with open(logfile_path, 'a') as f:
        f = open(logfile_path, 'a')
        _log('get stop command from {} and now requesting it to video server\n'.format(record_id), f)
        r = requests.post('http://127.0.0.1:{}/stop'.format(port), data={"record_id": record_id})
        _log('{}: {}\n'.format(time.ctime(time.time()), r.json()), f)
        if r.json()['code'] == 0:
            _log("{} stop succeeds and json info is {}".format(record_id, r.json()['info']), f)
            return True
        else:
            _log("{} stop failed and json info is {}".format(record_id, r.json()['info']), f)
            return False


def delete_block(record_id, logfile_path, start_id, end_id, port=5002):
    with open(logfile_path, 'a') as f:
        _log('get delete command from {} to delete {} to {} '
             'and now requesting it to video server\n'.format(record_id, start_id, end_id), f)
        _log('delete block from {} to {}'.format(start_id, end_id), f)
        para = {'record_id': record_id, "start_block_id": start_id,\
                "end_block_id": end_id}
        r = requests.post('http://127.0.0.1:5002/delete'.format(port), data=para)
        _log('{}: {}\n'.format(time.ctime(time.time()), r.json()), f)

        if r.json()['code'] == 0:
            _log("{}'s delete succeed and json info is {}\n".format(record_id, r.json()['info']), f)
            return True
        else:
            _log("{}'s delete failed and json info is {}\n".format(record_id, r.json()['info']), f)
            return False


def combine_block(record_id, logfile_path, start_id, end_id, name, port=5002):
    with open(logfile_path, 'a') as f:
        _log('get combine command from {} to combine {} to {} and now '
             'requesting it to video server\n'.format(record_id, start_id, end_id), f)
        _log('combine block from {} to {} into {}'.format(start_id, end_id, name), f)
        para = {'name': name, 'record_id': record_id, 'start_block_id': start_id,
                'end_block_id': end_id, 'start_block_offset': 0,
                "end_block_offset": -1}
        r = requests.post('http://127.0.0.1:{}/process'.format(port), data=para)
        f.write('{}: {}\n'.format(time.ctime(time.time()), r.json()))
        if r.json()['code'] == 0:
            _log("{}'s({}) combination succeed and json info is {}\n".format(name, record_id, r.json()['info']), f)
            return True
        else:
            _log("{}'s({}) combination failed and json info is {}\n".format(name, record_id, r.json()['info']), f)
            return False


def append_block(record_id, logfile_path, block_id, old_name, new_name, port=5002):
    with open(logfile_path, 'a') as f:
        _log('get append request to append append_id {} to old_name {}'.format(block_id, old_name), f)
        _log('append block from {} to {}'.format(block_id, old_name), f)
        para = {'name': old_name, 'new_name': new_name, 'block_id': block_id, 'record_id': record_id}
        r = requests.post('http://127.0.0.1:{}/append'.format(port), data=para)
        if r.json()['code'] == 0:
            _log("{}'s append succeed and json info is {}\n".format(record_id, r.json()['info']), f)
            return True
        else:
            _log("{}'s append failed and json info is {}\n".format(record_id, r.json()['info']), f)
            return False


def sweep_floor(logfile_path, port=5002):
    with open(logfile_path, 'a') as f:
        r = requests.post('http://127.0.0.1:{}/sweepfloor'.format(port))
        if r.json()['code'] == 0:
            _log("sweep succeed and json info is {}\n".format(r.json()['info']), f)
            return True
        else:
            _log("sweep failed and json info is {}\n".format(r.json()['info']), f)
            return False


if __name__ == "__main__":
    print(start_record(10455))
