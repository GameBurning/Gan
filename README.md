# Gan
## ffmpeg API:

### start:

Endpoint [POST]: 

* http://127.0.0.1:5000/start

Params[Form-data] :  

* ```room_id``` 
* ```platform``` (only "panda" works now)
* ```output_config :  {"block_size": 20}``` (block_size is in seconds)

Return :

 
* code 200 - Success:
	* ```TimeStamp of start point of recording```
	* ```Record ID```
* code 204 - Fail 

### stop:

Endpoint [POST]: 

* http://127.0.0.1:5000/stop

Params[Form-data] :  

* ```record_id```

Return : 

* Code 200 - success
* Code 204 - Fail

### delete:

Endpoint [POST]: 

* http://127.0.0.1:5000/delete

Params[Form-data] :  

* ```record_id```
* ```start_block_id```
* ```end_block_id```

Return : 

* Code 200 - success
* Code 204 - Fail


### process:

Endpoint [POST]: 

* http://127.0.0.1:5000/process

Params[Form-data] :  

* ```record_id ``` 
* ```name ``` : the output file name you want it be
* ```start_block_id```
* ```start_block_offset ``` : in seconds, -1 means keep whole start block
* ```end_block_id ```
* ```end_block_offset ``` : in seconds, -1 means keep whole start block

Return :

 
* code 200 - Success:
	* ```finished```
* code 204 - Fail:	Some error information