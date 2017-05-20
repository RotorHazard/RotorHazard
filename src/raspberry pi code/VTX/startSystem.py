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
rssi = [] # Current rssi value
lapCount = [] # Current lap count
try:
	cursor.execute("SELECT * FROM `nodes`") # Update to remove * and just get i2cAddr
	numNodes = int(cursor.rowcount)
	print "numNodes: %d" % numNodes
	for x in range(0, numNodes):
		row = cursor.fetchone()
		print row
		i2cAddr.append(int(row[1]))
		rssi.append(0) # Create array size to match number of nodes
		lapCount.append(0) # Create array size to match number of nodes
	print "i2cAddr: "
	print i2cAddr
except MySQLdb.Error as e:
	print e
except MySQLdb.Warning as e:
	print e

# Reset node lapCount, this is also set to zero in 'startRace.py'
try:
	cursor.execute("UPDATE `nodesMem` SET `lapCount` = 0")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

# Initialize systemStatus at 1 to start while loop
systemStatus = 1
try:
	cursor.execute("UPDATE `status` SET `systemStatus` = 1")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

# Initialize raceStatus at 0 to wait for 'start race' button
raceStatus = 0 
try:
	cursor.execute("UPDATE `status` SET `raceStatus` = 0")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e



# Main while loop
while systemStatus == 1:
	startTime = time.time()
	print " "
	print "Starting while loop."

	# Read systemStatus to know when to exit the loop
	# Read raceStatus from database to know when to check nodes for laps
	try:
		cursor.execute("SELECT * FROM `status`") # Update to remove * and just get the two variables
		results = cursor.fetchall() # Fetch all the rows in a list of lists.
		for row in results:
			systemStatus = row[0]
			raceStatus = row[1]
		db.commit()
	except MySQLdb.Error as e:
		print e
	except MySQLdb.Warning as e:
		print e

	# Read lapCounts because website buttons can reset them to zero
	try:
		cursor.execute("SELECT `lapCount` FROM `nodesMem`")
		numNodes = int(cursor.rowcount)
		for x in range(0, numNodes):
			row = cursor.fetchone()
			print row
			lapCount[x] = int(row[0])
	except MySQLdb.Error as e:
		print e
	except MySQLdb.Warning as e:
		print e

	# Loop for polling each node
	for x in range(0, numNodes):
		print "i2c address: %d" % (i2cAddr[x])

		# Node request: rssi
		try:
			i2cData = i2c.read_i2c_block_data(i2cAddr[x], 0x01, 1) # Arduino get rssi
			rssi[x] = i2cData[0]
			print "  rssi: %d" % (rssi[x])
		except IOError as e:
			print e
		time.sleep(0.100) # i2c data read delay

		# Only check lap data if race started
		if raceStatus == 1:
			# Node request: lap count and time in ms
			try:
				i2cData = i2c.read_i2c_block_data(i2cAddr[x], 0x02, 5) # Arduino get lap count and lap time in ms
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
						cursor.execute("UPDATE `nodesMem` SET `lapCount` = %s WHERE `node` = %s",(lapCount[x],x+1))
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
			time.sleep(0.100) # i2c data read delay
	
	# Update all rssi values at once to lessen database load
	try:
		sql = "UPDATE `nodesMem` SET `rssi` = %s WHERE `node` = %s"
		params = []
		for x in range(0, numNodes):
			params.append((rssi[x],x+1))
		cursor.executemany(sql, params)
		db.commit()
	except MySQLdb.Error as e:
		print e
		db.rollback()
	except MySQLdb.Warning as e:
		print e

	time.sleep(0.500) # main while loop delay
	
	endTime = time.time()
	print("Loop time: ", endTime - startTime)

db.close()