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
lapCount = []
try:
	cursor.execute("SELECT * FROM `nodes`");
	numNodes = int(cursor.rowcount)
	print "numNodes: %d" % numNodes
	for x in range(0, numNodes):
		row = cursor.fetchone()
		print row
		i2cAddr.append(int(row[1]))
		lapCount.append(int(row[5]))
	print "i2cAddr: "
	print i2cAddr
except MySQLdb.Error as e:
	print e
except MySQLdb.Warning as e:
	print e


# sets commsStatus true in the database
commsStatus = 1 # variable that will be updated from database
try:
	cursor.execute("UPDATE `setup` SET `commsStatus` = 1")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e


while commsStatus == 1:

	# read commsStatus and raceStatus
	try:
		cursor.execute("SELECT * FROM `setup`")
		results = cursor.fetchall() # Fetch all the rows in a list of lists.
		for row in results:
			commsStatus = row[0]
			raceStatus = row[1]
		db.commit()
	except MySQLdb.Error as e:
		print e
	except MySQLdb.Warning as e:
		print e
	
	# read lapCounts
	try:
		cursor.execute("SELECT `lapCount` FROM `nodes`");
		numNodes = int(cursor.rowcount)
		for x in range(0, numNodes):
			row = cursor.fetchone()
			print row
			lapCount[x] = int(row[0])
	except MySQLdb.Error as e:
		print e
	except MySQLdb.Warning as e:
		print e
	
	
	try:
		for x in range(0, numNodes): # loops for polling each node
			
			i2cBlockData = i2c.read_i2c_block_data(i2cAddr[x], 0x90, 5) # Request: rssi, lap, min, sec, ms
			time.sleep(0.5)

			print "for loop 'x': %d, i2c address: %d" % (x, i2cAddr[x])
			print i2cBlockData
			
			# Update rssi data in database
			try:
				cursor.execute("UPDATE `nodes` SET `rssi` = %s WHERE `node` = %s",(i2cBlockData[0],x+1))
				db.commit()
			except MySQLdb.Error as e:
				print e
				db.rollback()
			except MySQLdb.Warning as e:
				print e
			
			if raceStatus == 1:
				# lap data
				if i2cBlockData[1] != lapCount[x]: # Checks if the lap number is new
					# set lapCount to new lap
					try:
						cursor.execute("UPDATE `nodes` SET `lapCount` = %s WHERE `node` = %s",(i2cBlockData[1],x+1))
						db.commit()
					except MySQLdb.Error as e:
						print e
						db.rollback()
					except MySQLdb.Warning as e:
						print e					
					
					print "Adding lap to database."
					
					# Insert the lap data into the database
					try:
						cursor.execute("INSERT INTO `currentLaps` (`pilot`, `lap`, `min`, `sec`, `milliSec`) VALUES (%s, %s, %s, %s, %s)",(x+1, i2cBlockData[1], i2cBlockData[2], i2cBlockData[3], i2cBlockData[4]*10)) # ms was divided by 10 before sending
						db.commit()
					except MySQLdb.Error as e:
						print e
						db.rollback()
					except MySQLdb.Warning as e:
						print e
			
	except IOError as e:
		print e
		

	time.sleep(0.5) # main data loop delay
	
db.close()
