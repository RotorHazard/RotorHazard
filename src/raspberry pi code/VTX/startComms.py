# VTX Timer by Scott Chin
#
# Use to enable communications with the arduinos
#
# Starts the main comms loop

import smbus
import time
import MySQLdb

execfile("/home/pi/VTX/raceBoxConfig.py")

# Start i2c bus
i2c = smbus.SMBus(1)

# Varibales
commsStatus = 1 # initial define to get into main while loop
lapcounter = [0,0,0,0,0,0] # sets a reference point for checking new laps read from arduino below, change this to dynamic sizing based on numNodes from config file

# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()

# sets commsStatus true in the database
sql = "UPDATE setup SET commsStatus = 1 WHERE ID = 1"
try:
	cursor.execute(sql)
	db.commit()
except:
	db.rollback()

while commsStatus == 1:

	try:
		for x in range(0, numNodes): # loops for polling each node
			
			i2cBlockData = i2c.read_i2c_block_data(i2cAddr[x], 0x90, 5) # Request: rssi, lap, min, sec, ms
			time.sleep(0.25)
			
			# Update rssi data in database
			sql = "UPDATE nodes SET rssi = '%d' WHERE ID = '%d'" % (i2cBlockData[0],x+1)
			try:
				cursor.execute(sql)
				db.commit()
			except:
				db.rollback()
			
			# lap data
			if i2cBlockData[1] != lapcounter[x]: # Checks if the lap number is new
				lapcounter[x] = i2cBlockData[1] # set lapcounter to new lap
				print "Adding lap to database."
				# Insert the lap data into the database
				sql = "INSERT INTO currentrace(pilot, lap, min, sec, millisec) \
						VALUES ('%d', '%d', '%d', '%d', '%d' )" % \
						(x+1, i2cBlockData[1], i2cBlockData[2], i2cBlockData[3], i2cBlockData[4])
				try:
					cursor.execute(sql)
					db.commit()
				except:
					db.rollback()
			
			print "for loop 'x': %d, i2c address: %d" % (x, i2cAddr[x])
			print i2cBlockData
			
	except IOError as e:
		print e
		
	# read commsStatus and raceStatus
	sql = "SELECT * FROM setup WHERE ID = 1"
	try:
		cursor.execute(sql)
		results = cursor.fetchall() # Fetch all the rows in a list of lists.
		for row in results:
			commsStatus = row[1]
			raceStatus = row[2]
		db.commit()
	except:
		print "Error: unable to fecth data"
	
	time.sleep(0.25) # main data loop delay
	
db.close()
