import subprocess
import sys
import threading
from live_info.live_info import live_info_store
from live_info.live_info import get_stream_url
from flask import Flask
from flask import jsonify
from flask import request
import time

app = Flask(__name__)

room_platform_to_record_id = {}
threads = []
record_info = {}
lock = threading.Lock()

def start_download(url, file_prefix , record_id):
    command = "ffmpeg -i " + url +" -c copy -f segment -segment_time 20 -reset_timestamps 1 "+ file_prefix +"_%d.flv"
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    # Poll process for new output until finished
    while True:
        nextline = process.stdout.readline().decode("utf-8")

        if nextline == '' and process.poll() is not None:
            sys.stdout.write("no more lines!!!!!!!!!!!!!!")
            sys.stdout.flush()
            break
        if "Press [q] to stop" in nextline:
            print("starting recording......")
            lock.acquire()
            try:
                print("lock acquired......")
                record_info[record_id]["start_time"] = str(int(round(time.time() * 1000)))
                print("Start count TimeStamp : " + str(record_info[record_id]["start_time"]))
            finally:
                lock.release()

        sys.stdout.write(nextline)
        sys.stdout.flush()

    output = process.communicate()[0]
    exitCode = process.returncode

    if (exitCode == 0):
        return output
    else:
        return None

@app.route('/start', methods=['POST'])
def start():
    room_id = request.form.get('room_id', -1)
    platform = request.form.get('platform', "")
    output_config = request.form.get('output_config', "")
    print("room_id: " + str(room_id))
    print("platform: " + str(platform))
    print("output_config: " + str(output_config))

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

    if str(room_id) + str(platform) in room_platform_to_record_id:
        print("Already started")
        return "Already started", 204

    record_id = str(platform) + "_" + str(room_id) + "_" + str(int(round(time.time() * 1000)))
    room_platform_to_record_id[str(room_id) + str(platform)] = record_id
    record_info[record_id] = {"start_time" : ""}
    print("Assigned record_id : " + record_id)

    t = threading.Thread(target=start_download, args=[urls[0], record_id, record_id])
    threads.append(t)
    record_info[record_id]["thread"] = t
    t.start()

    while(True):
        lock.acquire()
        try:
            if record_info[record_id]["start_time"] != "":
                print('record_info[record_id]["start_time"] : ' + str(record_info[record_id]["start_time"]))
                break;
        finally:
            lock.release()
        time.sleep(1)

    return jsonify({'record_id' : '', 'start_time' : record_info[record_id]["start_time"] })

@app.route('/stop', methods=['POST'])
def stop():
    print("stop recording......")
    record_id = request.form.get('record_id', -1)
    print("record_id: " + str(record_id))

    if record_id == -1:
        return "", 204
    return jsonify({'record_id' : '', 'start_time' : '' })

@app.route('/delete', methods=['POST'])
def delete():
    print("delete records......")
    record_id = request.form.get('record_id', -1)
    start_block_id = request.form.get('start_block_id', -1)
    end_block_id = request.form.get('end_block_id', -1)
    print("record_id: " + str(record_id))
    print("start_block_id: " + str(start_block_id))
    print("end_block_id: " + str(end_block_id))

    if record_id == -1:
        return "", 204
    return jsonify({'record_id' : '', 'start_time' : '' })

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

threads = []

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
    app.run()

if __name__ == "__main__":
    main()
