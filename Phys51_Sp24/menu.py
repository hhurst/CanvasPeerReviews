#put in .zshrc 
#alias cpr='cd /Users/peteman/Nextcloud/Phys\ 51/Grades/CanvasPeerReviews; python menu.py'
import os, time
complete=False
relPath="."
theFile=""
print()
while theFile=="":
	files=[file for file in os.listdir(relPath) if ".py" in file and "menu" not in file and ".pyc" not in file and "credentials" not in file and "(conflicted" not in file and "shell.py" not in file and "path_info.py" not in file]
	folders=[item for item in os.listdir(relPath) if os.path.isdir(os.path.join(os.path.abspath("."), item)) and "__pycache__" not in item and "."!=item[0] and "Data" not in item]
	files.sort()
	folders.sort()
	if relPath==".":
		print("\t"+str(0) + ") python shell")
	else:
		print("\t"+str(0) + ") <- go back")
		
	for i,file in enumerate(files):
			print("\t"+str(i+1) + ") " + file.replace(".py",""))
	for j,folder in enumerate(folders):
			print("\t"+str(j+i+2) + ") " + folder + "...")
	print()
	val=int(input("which program do you want to run? "))-1
	if val<0 and relPath==".":
		theFile="shell.py"
	elif val<0:
		relPath="/".join(relPath.split("/")[:-1])
		print("\n\nlooking in " + relPath)
	elif val > i:
		relPath+="/"+folders[val-i-1] 
		print("\n\nlooking in " + relPath)
	else:
		theFile=relPath+"/"+files[val]

if relPath!=".":
	cmd='cp credentials.py "' + relPath +'/"'
	os.system(cmd)
	cmd='cp "path_info.py" "' + relPath +'/"'
	os.system(cmd)
start = time.perf_counter()
returnVal=os.system("python3 -i '" + theFile + "'")
end = time.perf_counter()
if (end-start)<1 and returnVal!=0:
	returnVal=os.system("python -i '" + theFile + "'")
if relPath!=".":
	cmd='rm "' + relPath +'/credentials.py"'
	os.system(cmd)
	cmd='rm "' + relPath +'/path_info.py"'
	os.system(cmd)
