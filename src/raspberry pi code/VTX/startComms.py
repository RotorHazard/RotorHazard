#
# Starts the main comms loop with the nodes, reads rssi and lap info from nodes, writes lap info to DB on new lap

import smbus
import time
import MySQLdb


# Start i2c bus
i2c = smbus.SMBus(1)


# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()


# Get nodes info
i2cAddr = []
try:
	cursor.execute("SELECT * FROM `nodes`");
	numNodes = int(cursor.rowcount)
	print "numNodes: %d" % numNodes
	for x in range(0, numNodes):
		row = cursor.fetchone()
		print row
		i2cAddr.append(int(row[1]))
	print "i2cAddr: "
	print i2cAddr
except:
	print "Error: unable to fetch data"


# Varibales
lapcounter = [0,0,0,0,0,0] # sets a reference point for checking new laps read from arduino below, change this to dynamic sizing based on numNodes from config file


# sets commsStatus true in the database
commsStatus = 1 # variable that will be updated from database
try:
	cursor.execute("UPDATE `setup` SET `commsStatus` = 1")
	db.commit()
except:
	db.rollback()


while commsStatus == 1:

	try:
		for x in range(0, numNodes): # loops for polling each node
			
			i2cBlockData = i2c.read_i2c_block_data(i2cAddr[x], 0x90, 5) # Request: rssi, lap, min, sec, ms
			time.sleep(0.5)
			
			# Update rssi data in database
			try:
				cursor.execute("UPDATE `nodes` SET `rssi` = %s WHERE `node` = %s",(i2cBlockData[0],x+1))
				db.commit()
			except:
				db.rollback()
			
			# lap data
			if i2cBlockData[1] != lapcounter[x]: # Checks if the lap number is new
				lapcounter[x] = i2cBlockData[1] # set lapcounter to new lap
				print "Adding lap to database."
				# Insert the lap data into the database
				try:
					cursor.execute("INSERT INTO `currentLaps` (`pilot`, `lap`, `min`, `sec`, `milliSec`) VALUES (%s, %s, %s, %s, %s)",(x+1, i2cBlockData[1], i2cBlockData[2], i2cBlockData[3], i2cBlockData[4]*10)) # ms was divided by 10 before sending
					db.commit()
				except:
					db.rollback()
			
			print "for loop 'x': %d, i2c address: %d" % (x, i2cAddr[x])
			print i2cBlockData
			
	except IOError as e:
		print e
		
	# read commsStatus and raceStatus
	try:
		cursor.execute("SELECT * FROM `setup`")
		results = cursor.fetchall() # Fetch all the rows in a list of lists.
		for row in results:
			commsStatus = row[0]
			raceStatus = row[1]
		db.commit()
	except:
		print "Error: unable to fetch data"
	
	time.sleep(0.5) # main data loop delay
	
db.close()
