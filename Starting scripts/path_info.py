#################  Set up where to find the relevant files  #################
import sys, os
os.chdir(os.path.dirname(os.path.realpath(__file__))) # work in the path the script was run from
homeFolder = os.path.expanduser('~')				  # get the home folder 
sys.path.insert(0, homeFolder + '/Documents/GitHub/CanvasPeerReviews')	# location of the module files.  Only necessary if they are stored somewhere other than the scripts
#RELATIVE_DATA_PATH='/Nextcloud/Phys 51/CanvasPeerReviews/Data/' #data directory relative to the home folder where your class data will be stored
#DATADIRECTORY=homeFolder  + RELATIVE_DATA_PATH
DATADIRECTORY="./Data/"
