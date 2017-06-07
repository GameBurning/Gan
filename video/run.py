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
from shutil import copyfile


if str(sys.version_info[0]) != "3":
    raise "Please Use Python _3_ !!!"

app = Flask(__name__)

log_file = open("recording_log.txt", "w")
log_file.write("$Process Started at : {}\n".format(time.ctime()))

output_dir = "output"
record_info = {}
lock = threading.Lock()
log_lock = threading.Lock()
range_to_combined_hashtable = {}

REC_STATUS_STOPPED = "stopped"
REC_STATUS_ERROR = "error"
REC_STATUS_RECORDING = "recording"
REC_STATUS_READY = "ready"

convert_command = 'cd output/process_results; for i in *.flv; do if [ ! -e $i.mov ]; then ffmpeg -y -i $i -ar 44100 $i.mov; fi; done'

# Use lock to synchronize threads on writing file
# Did not choose Queue with Producer & Customer pattern because Python3 Queue is acutally using a lock to protect q.put and q.get
# Since our use case is simple, no need to involve extra layer of work
def log_line(str):
    log_lock.acquire()
    try:
        log_file.write(str+'\n')
    except:
        pass
    log_lock.release()

def log_and_print_line(str):
    log_line(str)
    print(str+'\n')

@app.after_request
def after(response):
    log_and_print_line("time={}; type=RESPONSE; method={}; url={}; status={}; response={}".format(time.ctime(),request.method,request.base_url,response.status, response.data))
    return response

@app.before_request
def before():
    log_and_print_line("time={}; type=REQUEST; method={}; url={}; form={}".format(time.ctime(),request.method,request.base_url,request.form))
    pass

def terminated(process):
    return process.poll() is not None

def split_video(source_file, cut_offset, dst1, dst2):
    command1 = 'ffmpeg -y -i "{}" -vcodec copy -acodec copy -t {} "{}"'.format(source_file, cut_offset, dst1)
    command2 = 'ffmpeg -y -ss {} -i "{}" -vcodec copy -acodec copy "{}"'.format(cut_offset, source_file, dst2)

    process1 = subprocess.Popen(command1, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    process2 = subprocess.Popen(command2, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    process1.wait()
    process2.wait()

    return 0

def append_to_processed(name, record_id, block_id, new_name):
    processed_file_name = output_dir + '/process_results/'+name+'.flv'
    block_file_name = output_dir + '/'+ record_id+'/'+str(block_id)+'.flv'
    output_file_name = output_dir + '/process_results/'+new_name+'.flv'

    list_file_name = output_dir + '/append_'+record_id+block_id+new_name+str(int(time.time()))+ ".txt"

    if (not os.path.exists(processed_file_name)) or (not os.path.exists(block_file_name)):
        log_and_print_line("no processed file:{} or block file:{} ".format(processed_file_name, block_file_name))
        return 1

    list_file = open(list_file_name, "w")
    list_file.write("file " + 'process_results/'+name+'.flv\n')
    list_file.write("file " + record_id+'/'+str(block_id)+'.flv\n')
    list_file.close()

    command = "ffmpeg -y -f concat -i {} -vcodec copy -acodec copy {}".format(list_file_name, output_file_name)

    p = subprocess.Popen(command, shell=True)
    p.wait()

    try:
        if os.path.exists(processed_file_name):
            os.remove(processed_file_name)
        if os.path.exists(list_file_name):
            os.remove(list_file_name)
    except:
        pass

    return 0

# offset    -1      keep whole video
def start_process(record_id, name, start_block_id , start_block_offset, end_block_id, end_block_offset):
    if not os.path.exists(output_dir + "/"+record_id):
        return -1, "no record exists"
    if not os.path.exists(output_dir + "/"+"process_results"):
        os.makedirs(output_dir + "/"+"process_results")

    output_file_name = output_dir + "/"+ "process_results/" + name + ".flv"
    start_file_name = output_dir + "/"+ record_id + "/"+ str(start_block_id) + ".flv"
    end_file_name = output_dir + "/"+ record_id + "/"+ str(end_block_id) + ".flv"
    list_file_name = output_dir + "/"+ record_id + "/"+ name + "_" + str(int(time.time()))+ ".txt"

    if start_block_id > end_block_id:
        return -1, "start_block_id > end_block_id"
    elif start_block_id == end_block_id:
        if end_block_offset == -1 and start_block_offset == 0:
            copyfile(start_file_name, output_file_name)
        else:
            command = 'ffmpeg -y  -ss {} -i "{}" -t {} -vcodec copy -acodec copy "{}"'.format(start_block_offset, start_file_name, end_block_offset - start_block_offset + 1, output_file_name)
            process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            process.wait()

    else:
        list_file = open(list_file_name, "w")

        print("\n" + str(start_block_offset)+"\n")
        if start_block_offset != 0:
            split_video( \
                start_file_name, \
                start_block_offset, \
                output_dir + "/"+ record_id+"/"+ str(start_block_id) + "_cut_1.flv", \
                output_dir + "/"+ record_id+"/"+ str(start_block_id)+"_cut_2.flv" \
            )
            list_file.write("file " + str(start_block_id) + "_cut_2.flv\n")
        else:
            list_file.write("file " + str(start_block_id) + ".flv\n")

        start_block_id = int(start_block_id)
        end_block_id = int(end_block_id)

        if end_block_id > start_block_id + 1:
            for i in range(start_block_id + 1, end_block_id):
                list_file.write("file " + str(i) + ".flv\n")

        if end_block_offset != -1:
            split_video( \
                end_file_name, \
                end_block_offset, \
                output_dir + "/"+ record_id+"/"+ str(end_block_id)+"_cut_1.flv", \
                output_dir + "/"+ record_id+"/"+ str(end_block_id)+"_cut_2.flv" \
            )
            list_file.write("file " + str(end_block_id) + "_cut_1.flv\n")
        else:
            list_file.write("file " + str(end_block_id) + ".flv\n")

        list_file.close()
        command = "ffmpeg -y -f concat -i {} -vcodec copy -acodec copy {}".format(list_file_name, output_file_name)

        process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        process.wait()

    f1_1 = output_dir + "/"+ record_id+"/"+ str(start_block_id) + "_cut_1.flv";
    f1_2 = output_dir + "/"+ record_id+"/"+ str(start_block_id) + "_cut_2.flv";
    f2_1 = output_dir + "/"+ record_id+"/"+ str(end_block_id) + "_cut_1.flv";
    f2_2 = output_dir + "/"+ record_id+"/"+ str(end_block_id) + "_cut_2.flv";

    try:
        if os.path.exists(list_file_name):
            os.remove(list_file_name)
        if os.path.exists(f1_1):
            os.remove(f1_1)
        if os.path.exists(f1_2):
            os.remove(f1_2)
        if os.path.exists(f2_1):
            os.remove(f2_1)
        if os.path.exists(f2_2):
            os.remove(f2_2)
    except:
        pass

    return None

def start_download(url, record_id, block_size):
    try:
        os.makedirs(output_dir + "/"+record_id)
    except OSError:
        print("cannot make dir : " + output_dir + "/"+record_id)
        return

    command = 'ffmpeg -y -i "' + url +'" -c copy -sample_rate 44100 -f segment -segment_time ' + str(block_size) + ' -reset_timestamps 1 "'+ output_dir +"/"+record_id+"/" +'%d.flv"'
    log_and_print_line("time={}; ffmpeg_command={}".format(time.ctime(), command))

    lock.acquire()
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    record_info[record_id]["ffmpeg_process_handler"] = process
    lock.release()

    # Poll process for new output until finished
    while True:
        nextline = process.stdout.readline().decode("utf-8")
        sys.stdout.write(nextline)
        sys.stdout.flush()

        if nextline == '' and terminated(process):
            lock.acquire()
            # Stopped by "/stop" endpoint
            if record_info[record_id]["status"] == REC_STATUS_STOPPED:
                record_info.pop(record_id, None)
            else:
                record_info[record_id]["status"] = REC_STATUS_ERROR
                record_info[record_id]["ffmpeg_process_handler"] = None
            lock.release()
            break

        if "error" in nextline:
            print("error in getting streaming data...")
            lock.acquire()
            record_info[record_id]["status"] = REC_STATUS_READY
            record_info[record_id]["ffmpeg_process_handler"] = None
            lock.release()
            break

        if "Press [q] to stop" in nextline:
            print("..........starting recording id : " + str(record_id))
            lock.acquire()
            record_info[record_id]["status"] = REC_STATUS_RECORDING
            record_info[record_id]["start_time"] = str(int(time.time()))
            lock.release()

    return None

def worker_convert_format_in_processed_folder():
    while True:
        # 1 hour
        time.sleep(3600)
        # Convert
        log_and_print_line("time={};event=converting_processed_video;".format(time.ctime()))
        p1 = subprocess.Popen(convert_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        p1.wait()

    return None

@app.route('/start', methods=['POST'])
def start():
    _room_id = request.form.get('room_id', -1)
    _platform = request.form.get('platform', "")
    _output_config = request.form.get('output_config', "")

    try:
        output_config = json.loads(_output_config)
    except ValueError:
        output_config = {"block_size" : 20}

    if "block_size" in output_config.keys():
        block_size = output_config["block_size"]
        if not isinstance( block_size, int ):
            return jsonify({"code": 1, "info" : "blocksize should be int"}), 200

    if _room_id == -1:
        return jsonify({"code": 1, "info" : "need room_id"}), 200

    if _platform not in live_info_store:
        return jsonify({"code": 1, "info" : "platform " + str(_platform) + " not in list : " + ', '.join(live_info_store.keys())}), 200

    urls = get_stream_url(_platform, _room_id)

    if not urls:
        return jsonify({"code": 1, "info" : "cannot get streaming url"}), 200

    record_id = str(_platform) + "_" + str(_room_id) + "_" + str(int(time.time()))

    log_and_print_line("time={}; event='assigned record_id'; record_id={};".format(time.ctime(),record_id))

    # status: ready, error, recording
    record_info[record_id] = { \
        "start_time" : "", \
        "status" : REC_STATUS_READY, \
        "thread": None, \
        "ffmpeg_process_handler" : None \
    }

    res = create_recording_thread(urls, record_id, block_size)

    if res != 0:
        return jsonify({"code": 1, "info" : "can not get streaming data"}), 200

    return jsonify({"code": 0, "info" : {'record_id' : record_id, 'start_time' : record_info[record_id]["start_time"] }}), 200

def create_recording_thread(urls, record_id, block_size):
    if len(urls) == 0:
        return 1
    t = threading.Thread(target=start_download, args=[urls[0], record_id, block_size])
    record_info[record_id]["thread"] = t
    t.start()

    while(True):
        lock.acquire()
        status = record_info[record_id]["status"]
        start_time = record_info[record_id]["start_time"]
        lock.release()

        if status == REC_STATUS_ERROR:
            print("Streaming download fail, try next url...")
            urls.pop(0)
            lock.acquire()
            record_info[record_id]["status"] = REC_STATUS_READY
            record_info[record_id]["thread"] = None
            record_info[record_id]["ffmpeg_process_handler"] = None
            lock.release()
            return create_recording_thread(urls, record_id, block_size)
        elif status == REC_STATUS_RECORDING:
            break;
        time.sleep(1)

    return 0

@app.route('/stop', methods=['POST'])
def stop():
    record_id = request.form.get('record_id', -1)
    if record_id == -1:
        return jsonify({"code": 1, "info" : "need record_id"}), 200

    lock.acquire()
    if record_id in record_info and record_info[record_id]["ffmpeg_process_handler"] != None:
        os.kill(record_info[record_id]["ffmpeg_process_handler"].pid, signal.SIGKILL)
        for i in range(6):
            time.sleep(0.5)
            if terminated(record_info[record_id]["ffmpeg_process_handler"]):
                log_and_print_line("record_id={}; event=stop_successfully;".format(record_id))
                record_info[record_id]["status"] = REC_STATUS_STOPPED
                lock.release()
                return jsonify({"code": 0, "info" : REC_STATUS_STOPPED}), 200
    else:
        lock.release()
        return jsonify({"code": 1, "info" : "id not in record info or process handler is None"}), 200

    return jsonify({"code": 1, "info" : "stop failed or already stopped"}), 200

@app.route('/delete', methods=['POST'])
def delete():
    record_id = request.form.get('record_id', -1)
    start_block_id = request.form.get('start_block_id', -1)
    end_block_id = request.form.get('end_block_id', -1)
    try:
        t = int(start_block_id)
        t = int(end_block_id)
    except ValueError:
        return jsonify({"code": 1, "info" : "start_block_id, end_block_id should be integer number\n"}), 200

    if int(start_block_id) > int(end_block_id):
        return jsonify({"code": 1, "info" : "start_block_id should smaller or equal to end_block_id"}), 200

    if record_id == -1:
        return jsonify({"code": 1, "info" : "need record_id"}), 200

    for i in range(int(start_block_id), int(end_block_id)+1):
        try:
            os.remove(output_dir + "/"+ record_id + "/" + str(i) + ".flv")
        except:
            log_and_print_line("event=delete_fail; record_id={}; block_id={};".format(record_id, i))
            pass

    return jsonify({"code": 0, "info" : "deleted"}), 200

@app.route('/process', methods=['POST'])
def process():
    record_id = request.form.get('record_id', -1)
    start_block_id = request.form.get('start_block_id', -1)
    start_block_offset = request.form.get('start_block_offset', 0)
    end_block_id = request.form.get('end_block_id', -1)
    end_block_offset = request.form.get('end_block_offset', -1)
    name = request.form.get('name', str(record_id) +" - "+ str(start_block_id)+" : " + str(start_block_offset)+" - " + str(end_block_id) +" : " + str(end_block_offset) )

    if record_id == -1:
        return jsonify({"code": 1, "info" : "need record_id"}), 200

    try:
        start_block_id = int(start_block_id)
        end_block_id = int(end_block_id)
        start_block_offset = int(start_block_offset)
        end_block_offset = int(end_block_offset)
    except ValueError:
        return jsonify({"code": 1, "info" : "start_block_id, end_block_id, end_block_id, end_block_offset should be integer number\n"}), 200

    t = threading.Thread(target=start_process, args=[record_id, name, start_block_id, start_block_offset, end_block_id, end_block_offset])
    t.start()

    return jsonify({"code": 0, "info" : "finished"}), 200

@app.route('/append', methods=['POST'])
def append():
    name = request.form.get('name', -1)
    record_id = request.form.get('record_id', -1)
    block_id = request.form.get('block_id', -1)
    new_name = request.form.get('new_name', -1)

    if name == -1:
        return jsonify({"code": 1, "info" : "need name"}), 200
    if record_id == -1:
        return jsonify({"code": 1, "info" : "need record_id"}), 200
    if block_id == -1:
        return jsonify({"code": 1, "info" : "need block_id"}), 200
    if new_name == -1:
        return jsonify({"code": 1, "info" : "need new_name"}), 200

    if append_to_processed(name, record_id, block_id, new_name) == 0:
        return jsonify({"code": 0, "info" : "finished"}), 200
    else:
        return jsonify({"code": 1, "info" : "append fail"}), 200

@app.route('/convert', methods=['POST'])
def convert():
    log_and_print_line("time={};event=converting_processed_video;".format(time.ctime()))
    subprocess.Popen(convert_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return jsonify({"code": 0, "record_info":"start converting"}), 200

@app.route('/debug', methods=['POST'])
def debug():
    for k in record_info:
        if "ffmpeg_process_handler" in record_info[k] and record_info[k]["ffmpeg_process_handler"] != None:
            record_info[k]["ffmpeg PID"] = record_info[k]["ffmpeg_process_handler"].pid
        else:
            record_info[k].pop('ffmpeg PID', None)
    return jsonify({"code": 0, "record_info":str(record_info)}), 200

def main():
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    t = threading.Thread(target=worker_convert_format_in_processed_folder, args=[])
    t.start()
    app.run(port=5002)

if __name__ == "__main__":
    main()
