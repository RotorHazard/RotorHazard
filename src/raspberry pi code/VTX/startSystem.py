#
# Starts the main comms loop with the nodes, reads rssi and lap info from nodes, writes lap
# info to DB on new lap

import smbus
import time
import MySQLdb

# Start i2c bus
i2c = smbus.SMBus(1)

# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()

# Get nodes info from database
i2cAddr = [] # I2C slave address
vtxFreq = [] # VTX frequency in mhz ## might not be needed
rssi = [] # Current rssi value
rssiTrigger = [] # Current rssi threshold trigger value ## might not be needed
lapCount = [] # Current lap count
try:
	cursor.execute("SELECT * FROM `nodes`")
	numNodes = int(cursor.rowcount)
	print "numNodes: %d" % numNodes
	for x in range(0, numNodes):
		row = cursor.fetchone()
		print row
		i2cAddr.append(int(row[1]))
		rssi.append(int(row[3]))
		lapCount.append(int(row[5])) # Why is this getting laps instead of resetting to zero?
	print "i2cAddr: "
	print i2cAddr
except MySQLdb.Error as e:
	print e
except MySQLdb.Warning as e:
	print e

# Sets systemStatus true in the database
systemStatus = 1 # Initialize at 1 to start while loop
try:
	cursor.execute("UPDATE `setup` SET `systemStatus` = 1")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

# Main while loop
while systemStatus == 1:
	print " "
	print "Starting while loop."

	# read systemStatus and raceStatus from database
	try:
		cursor.execute("SELECT * FROM `setup`")
		results = cursor.fetchall() # Fetch all the rows in a list of lists.
		for row in results:
			systemStatus = row[0]
			raceStatus = row[1]
		db.commit()
	except MySQLdb.Error as e:
		print e
	except MySQLdb.Warning as e:
		print e
	
	# Read lap counts
	try:
		cursor.execute("SELECT `lapCount` FROM `nodes`")
		numNodes = int(cursor.rowcount)
		for x in range(0, numNodes):
			row = cursor.fetchone()
			lapCount[x] = int(row[0])
	except MySQLdb.Error as e:
		print e
	except MySQLdb.Warning as e:
		print e
	
	# Loop for polling each node
	for x in range(0, numNodes):
		print "i2c address: %d" % (i2cAddr[x])

		# Request: rssi
		try:
			i2cData = i2c.read_byte_data(i2cAddr[x], 0x01) # Arduino get rssi
			time.sleep(0.100) # Small i2c data read delay
			rssi[x] = i2cData
			print "  rssi: %d" % (rssi[x])
		except IOError as e:
			print e
			time.sleep(0.100) # Delay for arduino to recover from error

		# Update rssi data in database
		try:
			cursor.execute("UPDATE `nodes` SET `rssi` = %s",(rssi[x]))
			db.commit()
		except MySQLdb.Error as e:
			print e
			db.rollback()
		except MySQLdb.Warning as e:
			print e

		# Only check lap data if race started
		if raceStatus == 1:
			# Request: get lap count and time in ms
			try:
				i2cData = i2c.read_i2c_block_data(i2cAddr[x], 0x02, 5) # Arduino get lap count and lap time in ms
				time.sleep(0.100) # Small i2c data read delay
				#lapCount[x] = i2cData[0]
				print "  lapCount: %d" % (i2cData[0])

				milliSeconds = 0 # Rebuild ms from four bytes
				partA = i2cData[1]
				partB = i2cData[2]
				partC = i2cData[3]
				partD = i2cData[4]
				milliSeconds = partA
				milliSeconds = (milliSeconds << 8) | partB
				milliSeconds = (milliSeconds << 8) | partC
				milliSeconds = (milliSeconds << 8) | partD
				print "  milliSeconds: %d" % (milliSeconds)

				if i2cData[0] != lapCount[x]: # Checks if the lap number is new
					# Set lapCount to new lap number and update nodes table
					lapCount[x] = i2cData[0]
					print "Updating node lapCount in database."
					try:
						cursor.execute("UPDATE `nodes` SET `lapCount` = %s WHERE `node` = %s",(i2cData[1],x+1))
						db.commit()
					except MySQLdb.Error as e:
						print e
						db.rollback()
					except MySQLdb.Warning as e:
						print e					
					
					# Calculate lap min/sec/ms and insert into the database
					m = int(milliSeconds / 60000)
					over = milliSeconds % 60000
					print "  minutes: %d" % (m)
					s = int(over / 1000)
					over = over % 1000
					print "  seconds: %d" % (s)
					ms = int(over)
					print "  milliseconds: %d" % (ms)

					print "Adding lap to currentLaps in database."
					try:
						cursor.execute("INSERT INTO `currentLaps` (`pilot`, `lap`, `min`, `sec`, `milliSec`) VALUES (%s, %s, %s, %s, %s)",(x+1, lapCount[x], m, s, ms))
						db.commit()
					except MySQLdb.Error as e:
						print e
						db.rollback()
					except MySQLdb.Warning as e:
						print e
			except IOError as e:
				print e
				time.sleep(0.100) #Delay for arduino to recover from error
	
	time.sleep(0.250) # main while loop delay
	
db.close()