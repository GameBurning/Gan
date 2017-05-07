import subprocess
import sys
import threading
from live_info.live_info import live_info_store
from live_info.live_info import get_stream_url
from flask import Flask
from flask import jsonify
from flask import request
import time
import os
import json
import signal

if str(sys.version_info[0]) != "3":
    raise "Please Use Python _3_ !!!"

app = Flask(__name__)

room_platform_to_record_id = {}
record_info = {}
lock = threading.Lock()

def start_download(url, file_prefix , record_id, block_size):
    if not os.path.exists(record_id):
        os.makedirs(record_id)
    command = "ffmpeg -i " + url +" -c copy -f segment -segment_time " + str(block_size) + " -reset_timestamps 1 ./"+record_id+"/"+ file_prefix +"%d.flv"
    lock.acquire()
    record_info[record_id]["ffmpeg_process_handler"] = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    process = record_info[record_id]["ffmpeg_process_handler"]
    lock.release()

    # Poll process for new output until finished
    while True:
        nextline = process.stdout.readline().decode("utf-8")
        sys.stdout.write(nextline)
        sys.stdout.flush()

        if nextline == '' and process.poll() is not None:
            lock.acquire()
            record_info[record_id]["status"] = "ready"
            record_info[record_id]["ffmpeg_process_handler"] = None
            lock.release()
            break

        if "error" in nextline:
            print("error in getting streaming data...")
            lock.acquire()
            record_info[record_id]["status"] = "error"
            record_info[record_id]["ffmpeg_process_handler"] = None
            lock.release()
            break

        if "Press [q] to stop" in nextline:
            print("..........starting recording id : " + str(record_id))
            lock.acquire()
            record_info[record_id]["status"] = "recording"
            record_info[record_id]["start_time"] = str(int(time.time()))
            lock.release()

    return None

@app.route('/start', methods=['POST'])
def start():
    room_id = request.form.get('room_id', -1)
    platform = request.form.get('platform', "")
    output_config = request.form.get('output_config', "")

    print("room_id: " + str(room_id))
    print("platform: " + str(platform))
    print("output_config: " + str(output_config))

    output_config = json.loads(output_config)

    block_size = 20

    if "block_size" in output_config.keys():
        block_size = output_config["block_size"]
        if not isinstance( block_size, int ):
            return "blocksize should be int", 204

    if room_id == -1:
        print("Need room_id")
        return "Need room_id", 204

    if platform not in live_info_store:
        print("Platform " + str(platform) + " not in list : " + str(live_info_store))
        return "Platform " + str(platform) + " not in list : " + str(live_info_store), 204

    urls = get_stream_url(platform, room_id)

    if not urls:
        print("cannot get streaming url")
        return "cannot get streaming url", 204

    tmp_name = str(room_id) + str(platform)
    if  tmp_name in room_platform_to_record_id and record_info[room_platform_to_record_id[tmp_name]]["status"] == "recording":
        print("Already started")
        return "Already started", 204

    record_id = str(platform) + "_" + str(room_id) + "_" + str(int(time.time()))
    room_platform_to_record_id[str(room_id) + str(platform)] = record_id
    # status: ready, error, recording
    record_info[record_id] = {"start_time" : "", "status" : "ready", "thread": None, "ffmpeg_process_handler" : None}
    print("Assigned record_id : " + record_id)

    res = create_recording_thread(urls, "", record_id, block_size)

    if res != 0:
        return "Can not get streaming data", 204

    return jsonify({'record_id' : record_id, 'start_time' : record_info[record_id]["start_time"] })

def create_recording_thread(urls, file_prefix, record_id, block_size):
    if len(urls) == 0:
        return 1
    t = threading.Thread(target=start_download, args=[urls[0], file_prefix, record_id, block_size])
    record_info[record_id]["thread"] = t
    t.start()

    while(True):
        lock.acquire()
        status = record_info[record_id]["status"]
        start_time = record_info[record_id]["start_time"]
        lock.release()

        if status == "error":
            print("Streaming download fail, try next url...")
            lock.acquire()
            urls.pop(0)
            record_info[record_id]["status"] = "ready"
            record_info[record_id]["thread"] = None
            lock.release()
            return create_recording_thread(urls, file_prefix, record_id)
        elif status == "recording":
            print('record_info[record_id]["start_time"] : ' + str(start_time))
            break;
        time.sleep(1)

    return 0

@app.route('/stop', methods=['POST'])
def stop():
    print("stop recording......")
    record_id = request.form.get('record_id', -1)
    print("record_id: " + str(record_id))

    if record_id == -1:
        return "need record_id", 204

    lock.acquire()
    if record_info[record_id]["status"] != "recording":
        lock.release()
        return "Already stopped", 204

    # record_info[record_id]["ffmpeg_process_handler"].kill()
    os.kill(record_info[record_id]["ffmpeg_process_handler"].pid, signal.SIGKILL)
    for i in range(6):
        time.sleep(0.5)
        if record_info[record_id]["ffmpeg_process_handler"].poll() is not None:
            record_info[record_id]["status"] = "ready"
            record_info[record_id]["ffmpeg_process_handler"] = None
            sys.stdout.flush()
            lock.release()
            return "stopped"
    lock.release()
    return "stop failed", 204


@app.route('/delete', methods=['POST'])
def delete():
    print("delete records......")
    record_id = request.form.get('record_id', -1)
    start_block_id = request.form.get('start_block_id', -1)
    end_block_id = request.form.get('end_block_id', -1)
    print("record_id: " + str(record_id))
    print("start_block_id: " + start_block_id)
    print("end_block_id: " + end_block_id)

    if not isinstance( start_block_id, int ):
        print("start_block_id is integer")

    if record_id == -1:
        return "", 204

    for i in range(int(start_block_id), int(end_block_id)+1):
        try:
            os.remove(record_id + "/" + str(i) + ".flv")
        except OSError as e:
            print(str(e))

    return "deleted", 200

@app.route('/process', methods=['POST'])
def process():
    print("process records......")
    record_id = request.form.get('record_id', -1)
    start_block_id = request.form.get('start_block_id', -1)
    start_block_offset = request.form.get('start_block_offset', 0)
    end_block_id = request.form.get('end_block_id', -1)
    end_block_offset = request.form.get('end_block_offset', -1)
    print("record_id:" + str(record_id))
    print("start_block_id: " + str(start_block_id))
    print("start_block_offset: " + str(start_block_offset))
    print("end_block_id: " + str(end_block_id))
    print("end_block_offset: " + str(end_block_offset))

    if record_id == -1:
        return "", 204
    return jsonify({'record_id' : '', 'start_time' : '' })

prefixs=["v1", "v2", "v3", "v4"]

urls = ["http://220.243.224.53/pl3.live.panda.tv/live_panda/9b2f7ed9e4c50e2c879d5582adb1f596.flv",
 "http://pl12.live.panda.tv/live_panda/a60c08c3c87fe77d3541f2b91fe0b3d7.flv",
 "http://pl12.live.panda.tv/live_panda/cb8887f5a48a943a6d1312c0cf10fd5d.flv",
 "http://pl12.live.panda.tv/live_panda/2c0b221f5f544d4c009d7167043b9e04.flv"]

# def _test():
#     print(live_info_store)
    # get_stream_url(room_id="1002829", platform = "panda")

def main():
    # for i in range(4):
    #     t = threading.Thread(target=start_download, args=[prefixs[i], urls[i]])
    #     threads.append(t)
    #     t.start()
    # for t in threads:
    #     t.join()
    # _test()
    if sys.version_info[0] < 3:
        raise "Must be using Python 3"
    app.run(port=5001)

if __name__ == "__main__":
    main()
