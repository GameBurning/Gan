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
import psutil, os

if str(sys.version_info[0]) != "3":
    raise "Please Use Python _3_ !!!"

app = Flask(__name__)

REC_STATUS_STOPPED = "stopped"
REC_STATUS_ERROR = "error"
REC_STATUS_RECORDING = "recording"
REC_STATUS_READY = "ready"
PublicLogID = "0"

public_log_file = open("recording_log_{}.txt".format(time.ctime()), "w")
public_log_file.write("$Process Started at : {}\n".format(time.ctime()))
log_file_store = {PublicLogID : public_log_file}

output_dir = "output"
record_info = {}
lock = threading.Lock()
log_lock = threading.Lock()
range_to_combined_hashtable = {}

convert_command = 'cd output/process_results; for i in *.flv; do if [ ! -e ../converted/$i.mov ]; then ffmpeg -y -i $i -ar 44100 ../converted/$i.mov; fi; done'

def kill_proc_tree(pid, including_parent=True):
    parent = psutil.Process(pid)
    children = parent.children(recursive=True)
    for child in children:
        child.kill()
    gone, still_alive = psutil.wait_procs(children, timeout=5)
    if including_parent:
        parent.kill()
        parent.wait(5)

# Use lock to synchronize threads on writing file
# Did not choose Queue with Producer & Customer pattern because Python3 Queue is acutally using a lock to protect q.put and q.get
# Since our use case is simple, no need to involve extra layer of work
def log_line(record_id=PublicLogID, str = ""):
    if record_id not in log_file_store:
        log_file_store[PublicLogID].write("wrong record_id {} in log_line".format(record_id)+'\n')
        print("wrong record_id {} in log_line".format(record_id)+'\n')
        return 1
    log_lock.acquire()
    try:
        log_file_store[record_id].write(str+'\n')
        log_file_store[record_id].flush()
    except:
        pass
    log_lock.release()
    return 0

def log_and_print_line(record_id=PublicLogID, str = ""):
    log_line(record_id, str)
    print(str+'\n')

@app.after_request
def after(response):
    log_and_print_line(request.form.get("record_id",None), "time={}; type=RESPONSE; method={}; url={}; status={}; response={}".format(time.ctime(),request.method,request.base_url,response.status, response.data))
    return response

@app.before_request
def before():
    log_and_print_line(request.form.get("record_id",None), "time={}; type=REQUEST; method={}; url={}; form={}".format(time.ctime(),request.method,request.base_url,request.form))
    pass

def terminated(process):
    return process.poll() is not None

def readFFmpegPipe(process):
    for line in iter(process.stderr.readline, b''):
        pass

def split_video(source_file, cut_offset, dst1, dst2):
    command1 = 'ffmpeg -y -i "{}" -vcodec copy -acodec copy -t {} "{}"'.format(source_file, cut_offset, dst1)
    command2 = 'ffmpeg -y -ss {} -i "{}" -vcodec copy -acodec copy "{}"'.format(cut_offset, source_file, dst2)

    process1 = subprocess.Popen(command1, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    process2 = subprocess.Popen(command2, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    process1.wait()
    process2.wait()

    return 0

def append_to_processed(name, record_id, block_id, new_name):
    processed_file_name = output_dir + '/process_results/'+name+'.flv'
    block_file_name = output_dir + '/'+ record_id+'/'+str(block_id)+'.flv'
    output_file_name = output_dir + '/process_results/'+new_name+'.flv'

    list_file_name = output_dir + '/append_'+record_id+"_"+block_id+"_"+new_name+"_"+str(int(time.time()))+ ".txt"

    if (not os.path.exists(processed_file_name)) or (not os.path.exists(block_file_name)):
        log_and_print_line(record_id, "no processed file:{} or block file:{} ".format(processed_file_name, block_file_name))
        return 1

    list_file = open(list_file_name, "w")
    list_file.write("file " + 'process_results/'+name+'.flv\n')
    list_file.write("file " + record_id+'/'+str(block_id)+'.flv\n')
    list_file.close()

    command = "ffmpeg -y -f concat -i {} -vcodec copy -acodec copy {}".format(list_file_name, output_file_name)
    log_and_print_line(record_id, "time={}; append_ffmpeg_command={}".format(time.ctime(), command))

    p = subprocess.Popen(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
        return 1, "no record exists"
    if not os.path.exists(output_dir + "/"+"process_results"):
        os.makedirs(output_dir + "/"+"process_results")
    if not os.path.exists(output_dir + "/"+"converted"):
        os.makedirs(output_dir + "/"+"converted")
    output_file_name = output_dir + "/"+ "process_results/" + name + ".flv"
    start_file_name = output_dir + "/"+ record_id + "/"+ str(start_block_id) + ".flv"
    end_file_name = output_dir + "/"+ record_id + "/"+ str(end_block_id) + ".flv"
    list_file_name = output_dir + "/"+ record_id + "/"+ name + "_" + str(int(time.time()))+ ".txt"

    if start_block_id > end_block_id:
        return 1, "start_block_id > end_block_id"
    elif start_block_id == end_block_id:
        if end_block_offset == -1 and start_block_offset == 0:
            copyfile(start_file_name, output_file_name)
        else:
            command = 'ffmpeg -y  -ss {} -i "{}" -t {} -vcodec copy -acodec copy "{}"'.format(start_block_offset, start_file_name, end_block_offset - start_block_offset + 1, output_file_name)
            log_and_print_line(record_id, "time={}; process_ffmpeg_command={}".format(time.ctime(), command))
            process = subprocess.Popen(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            process.wait()

    else:
        list_file = open(list_file_name, "w")

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
        log_and_print_line(record_id, "time={}; process_ffmpeg_command={}".format(time.ctime(), command))

        process = subprocess.Popen(command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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

    return 0, "finished"

def start_download(url, record_id, block_size):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    try:
        if not os.path.exists(output_dir + "/"+record_id):
            os.makedirs(output_dir + "/"+record_id)
    except OSError:
        log_and_print_line(record_id, "time={};event=cannot_make_dir_{}".format(time.ctime(),output_dir + "/"+record_id))
        return 1, "error when mkdir"

    command = 'ffmpeg -y -i "' + url + '" -c copy -sample_rate 44100 -f segment -segment_time ' + str(block_size) + ' -reset_timestamps 1 "' + output_dir + "/" + record_id + "/" + '%d.flv"'

    log_and_print_line(record_id, "time={}; start_ffmpeg_command={}".format(time.ctime(), command))

    process = subprocess.Popen(command, shell=True, stderr=subprocess.PIPE)

    lock.acquire()
    record_info[record_id]["ffmpeg_process_handler"] = process
    record_info[record_id]["PID"] = record_info[record_id]["ffmpeg_process_handler"].pid
    record_info[record_id]["status"] = REC_STATUS_RECORDING
    lock.release()

    for line in iter(process.stderr.readline, b''):
        stdline = line.decode("utf-8")
        if "Press [q] to stop" in stdline:
            lock.acquire()
            record_info[record_id]["status"] = REC_STATUS_RECORDING
            record_info[record_id]["start_time"] = str(int(time.time()))
            lock.release()
            log_and_print_line(record_id, "time={}; event=started_recording".format(time.ctime()))
            t = threading.Thread(target=readFFmpegPipe, args=[process])
            t.start()
            return 0, "started"
        elif ("error" in stdline) or ("Error" in stdline) or ("ERROR" in stdline):
            lock.acquire()
            record_info[record_id]["status"] = REC_STATUS_READY
            record_info[record_id]["ffmpeg_process_handler"] = None
            lock.release()
            log_and_print_line(record_id, "time={}; event=error_start_recording_{}".format(time.ctime(),stdline))
            t = threading.Thread(target=readFFmpegPipe, args=[process])
            t.start()
            return 1, "cannot start" + stdline

    log_and_print_line(record_id, "time={}; event=no std lines read".format(time.ctime()))
    t = threading.Thread(target=readFFmpegPipe, args=[process])
    t.start()
    return 1, "Fail"


def create_recording_with_list(urls, record_id, block_size):
    if len(urls) == 0:
        return 1, "Fail"

    res = start_download(urls[0], record_id, block_size)

    if res[0] == 0:
        return res
    else:
        log_and_print_line(record_id, "time={};event=Streaming_download_fail_try_next_url;".format(time.ctime()))
        urls.pop(0)
        lock.acquire()
        record_info[record_id]["status"] = REC_STATUS_READY
        record_info[record_id]["ffmpeg_process_handler"] = None
        lock.release()
        return create_recording_with_list(urls, record_id, block_size)

def worker_convert_format_in_processed_folder():
    while True:
        # 1 hour
        time.sleep(3600)
        # Convert
        log_and_print_line(PublicLogID, "time={};event=converting_processed_video;".format(time.ctime()))
        p = subprocess.Popen(convert_command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return 1, "Fail"

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

    record_id = str(_platform) + "_" + str(_room_id) + "_" + str(int(time.time()))

    if not urls:
        return jsonify({"code": 1, "info" : "cannot get streaming url"}), 200

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    try:
        if not os.path.exists(output_dir + "/"+record_id):
            os.makedirs(output_dir + "/"+record_id)
    except OSError:
        log_and_print_line("time={};event=cannot_make_dir_{}".format(time.ctime(),output_dir + "/"+record_id))
        return 1, "error when mkdir"

    log_file_store[record_id] = open(output_dir + "/{}/_log_{}.txt".format(record_id, record_id), "w")

    log_and_print_line(record_id, "time={}; event='assigned record_id'; record_id={};".format(time.ctime(),record_id))

    # status: ready, error, recording
    record_info[record_id] = { \
        "start_time" : "", \
        "status" : REC_STATUS_READY, \
        "platform": _platform, \
        "ffmpeg_process_handler" : None \
    }


    res = create_recording_with_list(urls, record_id, block_size)

    if res[0] != 0:
        return jsonify({"code": 1, "info" : "can not get streaming data :" + res[1]}), 200

    return jsonify({"code": 0, "info" : {'record_id' : record_id, 'start_time' : record_info[record_id]["start_time"] }}), 200

@app.route('/stop', methods=['POST'])
def stop():
    record_id = request.form.get('record_id', -1)
    if record_id == -1:
        return jsonify({"code": 1, "info" : "need record_id"}), 200

    lock.acquire()
    if (record_id in record_info) and (record_info[record_id]["ffmpeg_process_handler"] != None) and (not terminated(record_info[record_id]["ffmpeg_process_handler"])):
        # os.kill(record_info[record_id]["ffmpeg_process_handler"].pid, signal.SIGKILL)
        # record_info[record_id]["ffmpeg_process_handler"].kill()
        kill_proc_tree(record_info[record_id]["PID"])
        for i in range(6):
            time.sleep(0.5)
            if terminated(record_info[record_id]["ffmpeg_process_handler"]):
                log_and_print_line(record_id, "time={}; record_id={}; event=stop_successfully;".format(time.ctime(),record_id))
                record_info[record_id]["status"] = REC_STATUS_STOPPED
                lock.release()
                return jsonify({"code": 0, "info" : REC_STATUS_STOPPED}), 200
    else:
        lock.release()
        return jsonify({"code": 1, "info" : "id not in record info or process handler is None"}), 200

    lock.release()
    return jsonify({"code": 1, "info" : "time outstop failed or already stopped"}), 200

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

    if record_id == -1:
        return jsonify({"code": 1, "info" : "need record_id"}), 200

    if int(start_block_id) > int(end_block_id):
        return jsonify({"code": 1, "info" : "start_block_id should smaller or equal to end_block_id"}), 200

    failed = False
    fail_info = []
    for i in range(int(start_block_id), int(end_block_id)+1):
        file_name = output_dir + "/"+ record_id + "/" + str(i) + ".flv"
        try:
            os.remove(file_name)
        except Exception as e:
            failed = True
            files_in_dir = '; '.join(os.listdir(output_dir + "/"+ record_id))
            log_and_print_line(record_id, "time={}; event=delete_fail; record_id={}; block_id={}; filesInDir={}".format(time.ctime(), record_id, i, files_in_dir))
            fail_info.append("time={}; event=delete_fail; record_id={}; block_id={}; filesInDir={}".format(time.ctime(), record_id, i, files_in_dir))

    if failed:
        return jsonify({"code": 1, "fail_list" : fail_info}), 200
    else :
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

    res = start_process(record_id, name, start_block_id, start_block_offset, end_block_id, end_block_offset)
    if res[0] == 0:
        return jsonify({"code": 0, "info" : "finished"}), 200
    else:
        return jsonify({"code": 1, "info" : res[1]}), 200

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

    t = threading.Thread(target=append_to_processed, args=[name, record_id, block_id, new_name])
    t.start()

    return jsonify({"code": 0, "info" : "finished"}), 200

@app.route('/convert', methods=['POST'])
def convert():
    log_and_print_line("time={};event=convert;".format(time.ctime()))
    subprocess.Popen(convert_command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return jsonify({"code": 0, "record_info":"start converting"}), 200

@app.route('/sweepfloor', methods=['POST'])
def sweepfloor():
    clean_backup_command = "rm output/backup/process_results/*.mov; rm output/backup/converted/*.mov;"
    mov_process_command = "mv output/process_results/*.flv output/backup/process_results/"
    mov_converted_command = "mv output/converted/*.mov output/backup/converted/"
    rm_recording_command = "rm -r output/panda_*; rm -r output/douyu_*; rm -r output/zhanqi_*; "

    if not os.path.exists(output_dir + "/"+"backup"):
        os.makedirs(output_dir + "/"+"backup")
    if not os.path.exists(output_dir + "/"+"backup"+ "/"+"process_results"):
        os.makedirs(output_dir + "/"+"backup"+ "/"+"process_results")
    if not os.path.exists(output_dir + "/"+"backup"+ "/"+"converted"):
        os.makedirs(output_dir + "/"+"backup"+ "/"+"converted")
    p = subprocess.Popen(clean_backup_command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    p.wait()

    subprocess.Popen(mov_process_command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.Popen(mov_converted_command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.Popen(rm_recording_command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return jsonify({"code": 0, "record_info":"start sweeping floor"}), 200

@app.route('/debug', methods=['POST'])
def debug():
    for k in record_info:
        if "ffmpeg_process_handler" in record_info[k] and record_info[k]["ffmpeg_process_handler"] != None:
            record_info[k]["PID"] = record_info[k]["ffmpeg_process_handler"].pid
        else:
            record_info[k].pop('ffmpeg PID', None)
    return jsonify({"code": 0, "record_info":str(record_info)}), 200

def main():
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    if not os.path.exists(output_dir + "/"+"process_results"):
        os.makedirs(output_dir + "/"+"process_results")
    if not os.path.exists(output_dir + "/"+"converted"):
        os.makedirs(output_dir + "/"+"converted")
    if not os.path.exists(output_dir + "/"+"backup"):
        os.makedirs(output_dir + "/"+"backup")
    if not os.path.exists(output_dir + "/"+"backup"+ "/"+"process_results"):
        os.makedirs(output_dir + "/"+"backup"+ "/"+"process_results")
    if not os.path.exists(output_dir + "/"+"backup"+ "/"+"converted"):
        os.makedirs(output_dir + "/"+"backup"+ "/"+"converted")
    t = threading.Thread(target=worker_convert_format_in_processed_folder, args=[])
    t.start()
    app.run(port=5002)

if __name__ == "__main__":
    main()
