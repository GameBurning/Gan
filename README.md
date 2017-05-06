# Gan
##ffmpeg API:

###start:

Endpoint [POST]: 

* http://127.0.0.1:5000/start

Params[Form-data] :  

* ```room_id``` 
* ```platform``` (only "panda" works now)
* ```output_config``` (not working now)

Return :

 
* code 200 - Success:
	* ```TimeStamp of start point of recording```
	* ```Record ID```
* code 204 - Fail 

###stop:

Endpoint [POST]: 

* http://127.0.0.1:5000/stop

Params[Form-data] :  

* ```record_id```

Return : 

* Code 200 - success
* Code 204 - Fail

###delete:

Endpoint [POST]: 

* http://127.0.0.1:5000/delete

Params[Form-data] :  

* ```record_id```
* ```start_block_id```
* ```end_block_id```

Return : 

* Code 200 - success
* Code 204 - Fail
	