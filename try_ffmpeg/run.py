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
import copy

if str(sys.version_info[0]) != "3":
    raise "Please Use Python _3_ !!!"

app = Flask(__name__)

room_platform_to_record_id = {}
record_info = {}
lock = threading.Lock()

def split_video(source_file, cut_offset, dst1, dst2):
    print("spliting video")

    command1 = "ffmpeg -y -i {} -vcodec copy -acodec copy -t {} {}".format(source_file, cut_offset, dst1)
    command2 = "ffmpeg -y -ss {} -i {} -vcodec copy -acodec copy {}".format(cut_offset, source_file, dst2)

    process1 = subprocess.Popen(command1, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    process2 = subprocess.Popen(command2, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    process1.wait()
    process2.wait()

    return 0

# offset    -1      keep whole video
def start_process(record_id, name, start_block_id , start_block_offset, end_block_id, end_block_offset):
    print("..........starting process")
    if not os.path.exists(record_id):
        record_info[record_id]["processing_tasks"][name] = {"status" : "error", "info" : "record with id :" + record_id +" not exists"}
        return -1, "no record exists"
    if not os.path.exists("process_results"):
        os.makedirs("process_results")

    output_file_name = "process_results/" + name + ".flv"
    start_file_name = record_id + "/"+ str(start_block_id) + ".flv"
    end_file_name = record_id + "/"+ str(end_block_id) + ".flv"
    list_file_name = record_id + "/"+ name + ".txt"

    lock.acquire()
    record_info[record_id]["processing_tasks"][name]["status"] = "running"
    lock.release()

    if start_block_id > end_block_id:
        lock.acquire()
        record_info[record_id]["processing_tasks"][name] = {"status" : "error", "info" : "start_block_id > end_block_id"}
        lock.release()
        return -1, "start_block_id > end_block_id"
    elif start_block_id == end_block_id:
        command = "ffmpeg -y -i {} -ss {} -to {} -vcodec copy -acodec copy {}".format(start_file_name, start_block_offset, end_block_offset, output_file_name)
    else:
        list_file = open(list_file_name, "w")

        if start_block_offset != -1:
            split_video( \
                start_file_name, \
                start_block_offset, \
                record_id+"/"+ str(start_block_id) + "_cut_1.flv", \
                record_id+"/"+ str(start_block_id)+"_cut_2.flv" \
            )
            list_file.write("file " + str(start_block_id) + "_cut_2.flv\n")
            print("file " + str(start_block_id) + "_cut_2.flv")
        else:
            list_file.write("file " + str(start_block_id) + ".flv\n")

        start_block_id = int(start_block_id)
        end_block_id = int(end_block_id)

        if end_block_id > start_block_id + 1:
            for i in range(start_block_id + 1, end_block_id):
                list_file.write("file " + str(i) + ".flv\n")
                print("file " + str(i) + ".flv")

        if end_block_offset != -1:
            split_video( \
                end_file_name, \
                end_block_offset, \
                record_id+"/"+ str(end_block_id)+"_cut_1.flv", \
                record_id+"/"+ str(end_block_id)+"_cut_2.flv" \
            )
            list_file.write("file " + str(end_block_id) + "_cut_1.flv\n")
            print("file " + str(end_block_id) + "_cut_1.flv")
        else:
            list_file.write("file " + str(end_block_id) + ".flv\n")

        list_file.close()
        command = "ffmpeg -y -f concat -i {} -vcodec copy -acodec copy {}".format(list_file_name, output_file_name)

    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    # Poll process for new output until finished
    while True:
        nextline = process.stdout.readline().decode("utf-8")
        sys.stdout.write(nextline)
        sys.stdout.flush()

        if nextline == '' and process.poll() is not None:
            print("..........concatenate finished")
            try:
                os.remove(list_file_name)
            except OSError:
                pass
            lock.acquire()
            record_info[record_id]["processing_tasks"][name] = {"status" : "finished"}
            lock.release()
            break

        if "Press [q] to stop" in nextline:
            print("..........starting concatenating video")

        if "Impossible" in nextline:
            print("..........error in concatenating" + nextline)
            try:
                os.remove(output_file_name)
            except OSError:
                pass

            try:
                os.remove(list_file_name)
            except OSError:
                pass

            lock.acquire()
            record_info[record_id]["processing_tasks"][name] = {"status" : "error", "info" : nextline}
            lock.release()
            break

    return None


def start_download(url, file_prefix , record_id, block_size):
    if not os.path.exists(record_id):
        os.makedirs(record_id)
    command = "ffmpeg -y -i " + url +" -c copy -f segment -segment_time " + str(block_size) + " -reset_timestamps 1 ./"+record_id+"/"+ file_prefix +"%d.flv"
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
    if tmp_name in room_platform_to_record_id and record_info[room_platform_to_record_id[tmp_name]]["status"] == "recording":
        print("Already started")
        return "Already started", 204

    record_id = str(platform) + "_" + str(room_id) + "_" + str(int(time.time()))
    room_platform_to_record_id[str(room_id) + str(platform)] = record_id
    # status: ready, error, recording
    record_info[record_id] = { \
        "start_time" : "", \
        "status" : "ready", \
        "thread": None, \
        "ffmpeg_process_handler" : None, \
        "processing_tasks" : {} \
    }
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
            record_info[record_id]["block_size"] = block_size
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
    if (record_id not in record_info) or record_info[record_id]["status"] != "recording":
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
    name = request.form.get('name', str(record_id) +" - "+ str(start_block_id)+" : " + str(start_block_offset)+" - " + str(end_block_id) +" : " + str(end_block_offset) )

    if isinstance(start_block_offset, str):
        start_block_offset = int(start_block_offset)
    if isinstance(end_block_offset, str):
        end_block_offset = int(end_block_offset)

    print("record_id:" + str(record_id))
    print("start_block_id: " + str(start_block_id))
    print("start_block_offset: " + str(start_block_offset))
    print("end_block_id: " + str(end_block_id))
    print("end_block_offset: " + str(end_block_offset))
    print("name: " + name)

    if record_id == -1:
        return "", 204

    # start_process(record_id, name, start_block_id , start_block_offset, end_block_id, end_block_offset)
    lock.acquire()
    if record_id not in record_info:
        record_info[record_id] = { \
            "start_time" : "", \
            "status" : "ready", \
            "thread": None, \
            "ffmpeg_process_handler" : None, \
            "processing_tasks" : { name : {"status" : "", "info" : ""} } \
        }
    else:
        record_info[record_id]["processing_tasks"][name] = {"status" : "", "info" : ""}
    lock.release()

    t = threading.Thread(target=start_process, args=[record_id, name, start_block_id, start_block_offset, end_block_id, end_block_offset])
    t.start()

    for i in range(10):
        time.sleep(1)

        lock.acquire()
        process_task = copy.deepcopy( record_info[record_id]["processing_tasks"][name] )
        lock.release()

        if process_task["status"] == "error":
            return "processing error"+process_task["info"], 204
        elif process_task["status"] == "finished":
            return "finished", 200

    return "time out", 204

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
    app.run(port=5002)

    # if sys.version_info[0] < 3:
    #     raise "Must be using Python 3"


    # split_video("panda_66666_1494180289", "10", 5, "10_1", "10_2")

    # def start_process(record_id, name, start_block_id , start_block_offset, end_block_id, end_block_offset)
    # t = threading.Thread(target=start_process, args=["panda_642207_1494191313", "concatenated", 1, -1, 4, -1])
    # t.start()

if __name__ == "__main__":
    main()
