import subprocess
import sys
import threading
from live_info.live_info import live_info_store
from live_info.live_info import get_stream_url
from flask import Flask
from flask import jsonify
from flask import request

app = Flask(__name__)

def start_download(prefix, url):
    command = "ffmpeg -i " + url +" -c copy -f segment -segment_time 20 -reset_timestamps 1 "+ prefix +"_%d.flv"
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    # Poll process for new output until finished
    while True:
        nextline = process.stdout.readline()
        if nextline == '' and process.poll() is not None:
            sys.stdout.write("no more lines!!!!!!!!!!!!!!")
            sys.stdout.flush()
            break
        if(nextline.__contains__("Press [q] to stop")):
            print("Start count TimeStamp")
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
    print("starting recording......")
    room_id = request.form.get('room_id', -1)
    platform = request.form.get('platform', "")
    output_config = request.form.get('output_config', "")
    print("room_id: " + str(room_id))
    print("platform: " + str(platform))
    print("output_config: " + str(output_config))

    if room_id == -1:
        return "", 204
    return jsonify({'record_id' : '', 'start_time' : '' })

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

def _test():
    print(live_info_store)
    get_stream_url(room_id="1002829", platform = "panda")

def main():
    # for i in range(4):
    #     t = threading.Thread(target=start_download, args=[prefixs[i], urls[i]])
    #     threads.append(t)
    #     t.start()
    # for t in threads:
    #     t.join()
    _test()
    app.run()

if __name__ == "__main__":
    main()
