file = open("in.txt", "w+")
for i in range(29):
	file.write("file v1_"+`i`+".flv\n")
file.close()
