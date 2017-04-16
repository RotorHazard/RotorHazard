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
lapcounter = 0 # sets a reference point for checking new laps read from arduino below

# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()

# sets commsStatus true in the database
sql = "UPDATE setup SET commsStatus = 1 WHERE ID = 1"
try:
	cursor.execute(sql) # Execute the SQL command
	db.commit() # Commit your changes in the database
except:
	db.rollback() # Rollback in case there is any error

while commsStatus == 1:

	try:
		for x in range(0, numNodes): # loops for polling each node
			# rssi Data
			i2cBlockData = i2c.read_i2c_block_data(i2cAddr[x], 0xA0, 1) # Request rssi
			time.sleep(0.1)
			rssi = i2cBlockData[0]
			# Update rssi data in database
			sql = "UPDATE nodes SET rssi = '%d' WHERE ID = '%d'" % (rssi,x+1)
			try:
				cursor.execute(sql) # Execute the SQL command
				db.commit() # Commit your changes in the database
			except:
				db.rollback() # Rollback in case there is any error
			time.sleep(0.1)
	
			# lap data
			# add an if statement here to only check for laps data while raceStatus = true
			i2cBlockData = i2c.read_i2c_block_data(i2cAddr[x], 0x90, 4) # Request lap data: lap, min, sec, ms
			time.sleep(0.1)
			if i2cBlockData[0] != lapcounter: # Checks if the lap number is new
				# print "Lap %d %d:%d:%d" %(i2cBlockData[0],i2cBlockData[1],i2cBlockData[2],i2cBlockData[3])
				lapcounter = i2cBlockData[0]
				minutes = i2cBlockData[1]
				seconds = i2cBlockData[2]
				millisec = i2cBlockData[3]
				
				# Insert the lap data into the database
				sql = "INSERT INTO races(racegroup, race, pilot, lap, min, sec, millisec) \
						VALUES ('%d', '%d', '%d', '%d', '%d', '%d', '%d' )" % \
						(1, 1, x+1, lapcounter, minutes, seconds, millisec)
				try:
					cursor.execute(sql) # Execute the SQL command
					db.commit() # Commit your changes in the database
				except:
					db.rollback() # Rollback in case there is any error
			time.sleep(0.1)
		
		
	except IOError as e:
		print e
		
	
	
	
	# read commsStatus and raceStatus
	sql = "SELECT * FROM setup WHERE ID = 1"
	try:
		cursor.execute(sql) # Execute the SQL command
		results = cursor.fetchall() # Fetch all the rows in a list of lists.
		for row in results:
			commsStatus = row[1]
			raceStatus = row[2]
		db.commit()
	except:
		print "Error: unable to fecth data"
	
	time.sleep(0.1) # main data loop delay
	
db.close() # disconnect from server
