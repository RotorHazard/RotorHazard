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
	cursor.execute("SELECT `i2cAddr` FROM `nodes`")
	numNodes = int(cursor.rowcount) # Get the number of nodes in the system from the size of nodes table
	print "numNodes:"
	print numNodes
	results = cursor.fetchall() # Fetch all the rows in a list of lists
	for row in results:
		i2cAddr.append(int(row[0]))
		rssi.append(0) # Create array size to match number of nodes
		lapCount.append(0) # Create array size to match number of nodes
	print "i2cAddr:"
	print i2cAddr
	print "rssi:"
	print rssi
	print "lapCount:"
	print lapCount
except MySQLdb.Error as e:
	print e
except MySQLdb.Warning as e:
	print e

# Set node lapCount and rssi to zero on system start to fill MEMORY only tables
try:
	cursor.execute("DELETE FROM `nodesMem` WHERE 1")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e
for x in range(0, numNodes):
	try:
		cursor.execute("INSERT INTO `nodesMem` (`node`, `rssi`, `lapCount`) VALUES (%s,0,0)",(x+1))
		db.commit()
	except MySQLdb.Error as e:
		print e
		db.rollback()
	except MySQLdb.Warning as e:
		print e

# Get the current config: group, min lap time
try:
	cursor.execute("SELECT `group`, `minLapTime` FROM `config`")
	result = cursor.fetchone()
	group = int(result[0])
	minLapTime = int(result[1])
	print "group:"
	print group
	print "minLapTime:"
	print minLapTime
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

# Get the current group info: pilot, channel, trigger
pilot = []
vtxChan = []
rssiTrig = []
try:
	cursor.execute("SELECT `pilot`, `vtxChan`, `rssiTrigger` FROM `groups` WHERE `group` = %s",(group))
	results = cursor.fetchall() # Fetch all the rows in a list of lists
	for row in results:
		pilot.append(int(row[0]))
		vtxChan.append(str(row[1]))
		rssiTrig.append(int(row[2]))
	print "pilot:"
	print pilot
	print "vtxChan:"
	print vtxChan
	print "rssiTrig:"
	print rssiTrig
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

# Re-initialize arduinos with current group and config
for x in range(0, numNodes):
	vtxFreq = int(vtxChan[x].split()[1])
	partA = (vtxFreq >> 8) # Split vtxFreq into two bytes to send
	partB = (vtxFreq & 0xFF)
	i2c.write_i2c_block_data(i2cAddr[x], 0x51, [partA, partB]) # Initialize arduino defaults and set vtx frequency
	time.sleep(0.100)
	i2c.write_byte_data(i2cAddr[x], 0x53, rssiTrig[x]) # Arduino set rssi threshold
	time.sleep(0.100)
	i2c.write_byte_data(i2cAddr[x], 0x54, minLapTime) # Set min lap time in seconds
	time.sleep(0.100)

# Initialize systemStatus at 1 to start while loop
systemStatus = 1
# Initialize raceStatus at 0 to wait for 'start race' button
raceStatus = 0 
try:
	cursor.execute("DELETE FROM `status` WHERE 1")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e
try:
	cursor.execute("INSERT INTO `status` (`systemStatus`, `raceStatus`) VALUES (1,0)")
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
		cursor.execute("SELECT `systemStatus`, `raceStatus` FROM `status`")
		results = cursor.fetchall() # Fetch all the rows in a list of lists
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
		for x in range(0, numNodes):
			row = cursor.fetchone()
			lapCount[x] = int(row[0])
	except MySQLdb.Error as e:
		print e
	except MySQLdb.Warning as e:
		print e
	print "  lapCount:"
	print lapCount

	# Loop for polling each node
	for x in range(0, numNodes):
		print "i2c address: %d" % (i2cAddr[x])

		# Node request: rssi
		try:
			i2cData = i2c.read_i2c_block_data(i2cAddr[x], 0x01, 2) # Arduino get rssi
			rssi[x] = 0 # Rebuild rssi from two bytes
			partA = i2cData[0]
			partB = i2cData[1]
			rssi[x] = partA
			rssi[x] = (rssi[x] << 8) | partB
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
					
					# Calculate lap min/sec/ms
					m = int(milliSeconds / 60000)
					over = milliSeconds % 60000
					print "  minutes: %d" % (m)
					s = int(over / 1000)
					over = over % 1000
					print "  seconds: %d" % (s)
					ms = int(over)
					print "  milliseconds: %d" % (ms)

					# Add new lap to the database
					print "Adding lap to currentLaps in database."
					try:
						cursor.execute("INSERT INTO `currentLaps` (`pilot`, `lap`, `min`, `sec`, `milliSec`) VALUES (%s, %s, %s, %s, %s)",(pilot[x], lapCount[x], m, s, ms))
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

	time.sleep(0.500) # Main while loop delay
	
	endTime = time.time()
	print("Loop time: ", endTime - startTime)

db.close() # Disconnect from database
