import requests
import time
import logging


class Recorder:
    def __init__(self, name, logger):
        self.name = name
        self.logger = logger
        self.record_id = None

    def start_record(self, roomid, platform='panda', block_size=45, port=5002):
        self.logger.info('get start command for {} and now requesting it to video server\n'.format(roomid))
        para = {'room_id': roomid, 'platform': platform, 'output_config':'{"block_size":' + str(block_size) + '}'}
        r = requests.post('http://127.0.0.1:{}/start'.format(port), data=para)

        self.logger.info('{}: {}\n'.format(time.ctime(time.time()), r.json()))

        if r.json()['code'] == 0:
            self.logger.info("{}'s start succeed and json info is {}".format(roomid, r.json()['info']))
            self.record_id = r.json()['info']['record_id']
            return r.json()['info']['record_id'], r.json()['info']['start_time']
        else:
            self.logger.error("{}'s start failed and json info is {}".format(roomid, r.json()['info']))
            return -1, -1

    def stop_record(self, logfile_path, port=5002):
        f = open(logfile_path, 'a')
        self.logger.info('get stop command for {} and now requesting it to video server\n'.format(self.record_id))
        r = requests.post('http://127.0.0.1:{}/stop'.format(port), data={"record_id": self.record_id})
        self.logger.info('{}: {}\n'.format(time.ctime(time.time()), r.json()))
        if r.json()['code'] == 0:
            self.logger.info("{} stop succeeds and json info is {}".format(self.record_id, r.json()['info']))
            return True
        else:
            self.logger.error("{} stop failed and json info is {}".format(self.record_id, r.json()['info']))
            return False

    def delete_block(self, logfile_path, start_id, end_id, port=5002):
        self.logger.info('get delete command for {} to delete {} to {} '
             'and now requesting it to video server\n'.format(self.record_id, start_id, end_id))
        self.logger.info('delete block from {} to {}'.format(start_id, end_id))
        para = {'record_id': self.record_id, "start_block_id": start_id,\
                "end_block_id": end_id}
        r = requests.post('http://127.0.0.1:5002/delete'.format(port), data=para)
        self.logger.info('{}: {}\n'.format(time.ctime(time.time()), r.json()))

        if r.json()['code'] == 0:
            self.logger.info("{}'s delete succeed and json info is {}\n".format(self.record_id, r.json()['info']))
            return True
        else:
            self.logger.error("{}'s delete failed and json info is {}\n".format(self.record_id, r.json()['info']))
            return False

    def combine_block(self, logfile_path, start_id, end_id, name, port=5002):
        self.logger.info('get combine command for {} to combine {} to {} and now '
             'requesting it to video server\n'.format(self.record_id, start_id, end_id))
        self.logger.info('combine block from {} to {} into {}'.format(start_id, end_id, name))
        para = {'name': name, 'record_id': self.record_id, 'start_block_id': start_id,
                'end_block_id': end_id, 'start_block_offset': 0,
                "end_block_offset": -1}
        r = requests.post('http://127.0.0.1:{}/process'.format(port), data=para)
        f.write('{}: {}\n'.format(time.ctime(time.time()), r.json()))
        if r.json()['code'] == 0:
            self.logger.info("{}'s({}) combination succeed and json info is {}\n".format(name, self.record_id,
                                                                                         r.json()['info']))
            return True
        else:
            self.logger.error("{}'s({}) combination failed and json info is {}\n".format(name, self.record_id,
                                                                                        r.json()['info']))
            return False

    def append_block(self, logfile_path, block_id, old_name, new_name, port=5002):
        self.logger.info('get append request to append append_id {} to old_name {}'.format(block_id, old_name))
        self.logger.info('append block from {} to {}'.format(block_id, old_name))
        para = {'name': old_name, 'new_name': new_name, 'block_id': block_id, 'record_id': self.record_id}
        r = requests.post('http://127.0.0.1:{}/append'.format(port), data=para)
        if r.json()['code'] == 0:
            self.logger.info("{}'s append succeed and json info is {}\n".format(self.record_id, r.json()['info']))
            return True
        else:
            self.logger.error("{}'s append failed and json info is {}\n".format(self.record_id, r.json()['info']))
            return False

    def sweep_floor(self, port=5002):
        r = requests.post('http://127.0.0.1:{}/sweepfloor'.format(port))
        if r.json()['code'] == 0:
            self.logger.info("sweep succeed and json info is {}\n".format(r.json()['info']))
            return True
        else:
            self.logger.error("sweep failed and json info is {}\n".format(r.json()['info']))
            return False
