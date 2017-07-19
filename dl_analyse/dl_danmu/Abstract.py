import abc, threading, time, traceback, logging


# This client will auto-reload if exception is raised inside and write a log
# it is deprecated once used
# log of main start and thread is recorded
# If you want to close it outside, just set the deprecated flag to True
# Inside reload is controlled by self.live flag
# danmuWaitTime is wrapped in danmuThread
# this client may cause unclosed thread because of thread is blocked, but it's not a big problem
class AbstractDanMuClient(object):
    __metaclass__ = abc.ABCMeta

    def __init__(self, room_id, name, count_danmu_fn, logger, maxNoDanMuWait=90, anchorStatusRescanTime=30):
        self.roomID = room_id
        self.name = name
        self.maxNoDanMuWait = maxNoDanMuWait
        self.anchorStatusRescanTime = anchorStatusRescanTime
        self.deprecated = False  # this is an outer live flag
        self.live = False  # this is an inner live flag
        self.danmuSocket = None
        self.danmuThread, self.heartThread = None, None
        self.danmuWaitTime = -1
        self.danmuProcess = None
        self.countDanmuFn = count_danmu_fn
        self.logger = logger

    def start(self):
        self.logger.info("===========Socket thread of {} starts===========".format(self.name))
        while not self.deprecated:
            try:
                while not self.deprecated:
                    # if online then break
                    if self.get_live_status(): break
                    # if offline wait for sometime
                    time.sleep(self.anchorStatusRescanTime)
                # if stopped by outer client, then stop this function
                else:
                    break
                try:
                    danmuSocketInfo, roomInfo = self._prepare_env()
                except Exception as e:
                    self.logger.critical('prepare env failed and exception is {}'.format(e))
                    time.sleep(20)
                    continue
                if self.danmuSocket: self.danmuSocket.close()
                self.danmuWaitTime = -1
                self._init_socket(danmuSocketInfo, roomInfo)
                danmuThreadFn, heartThreadFn = self._create_thread_fn(roomInfo)
                self._wrap_thread(danmuThreadFn, heartThreadFn)
                self._start_receive()
            except Exception as e:
                self.logger.critical(traceback.format_exc())
                time.sleep(5)
            else:
                break

    def _socket_timeout(self, fn):
        # if socket went wrong, reload the whole client
        def __socket_timeout(*args, **kwargs):
            try:
                fn(*args, **kwargs)
            except Exception as e:
                self.logger.critical(traceback.format_exc())
                if not self.live: return
                self.live = False
                # In case thread is blocked and can't stop, set a max wait time
                waitEndTime = time.time() + 20
                while self.thread_alive() and time.time() < waitEndTime:
                    time.sleep(1)
                self.start()
        return __socket_timeout

    def _wrap_thread(self, danmuThreadFn, heartThreadFn):
        @self._socket_timeout
        def heart_beat(self):
            while self.live and not self.deprecated:
                heartThreadFn(self)

        @self._socket_timeout
        def get_danmu(self):
            while self.live and not self.deprecated:
                if self.danmuWaitTime != -1 and self.danmuWaitTime < time.time():
                    raise Exception('{} No danmu received in {}, and max wait time is {}'.format(self.name,
                                                                                                 self.maxNoDanMuWait,
                                                                                                 self.danmuWaitTime))
                danmuThreadFn(self)
        self.heartThread = threading.Thread(target = heart_beat, args = (self,))
        self.heartThread.setDaemon(True)
        self.danmuThread = threading.Thread(target = get_danmu, args = (self,))
        self.danmuThread.setDaemon(True)

    def _start_receive(self):
        self.live = True
        self.danmuThread.start()
        self.heartThread.start()
        self.danmuWaitTime = time.time() + self.maxNoDanMuWait

    def thread_alive(self):
        if self.danmuSocket is None or not self.danmuThread.isAlive():
            return False
        else:
            return True


    @abc.abstractmethod
    def get_live_status(self):
        return False # return whether anchor is on live

    @abc.abstractmethod
    def _prepare_env(self):
        return ('0.0.0.0', 80), {} # danmu, roomInfo

    @abc.abstractmethod
    def _init_socket(self, danmu, roomInfo):
        pass

    # method shouldn't include the main while loop
    # danmu method should reload self.danmuWaitTime
    @abc.abstractmethod
    def _create_thread_fn(self, roomInfo):
        return None, None # danmu, heart

class DanMuException(Exception):
    def __init__(self, message, *args, **kwargs):
        Exception.__init__(self)
        self.message = message
        self.args = args
    def __str__(self):
        return self.message
