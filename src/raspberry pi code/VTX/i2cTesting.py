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
	print " "
	print "Starting while loop."
	try:
		#for x in range(0, numNodes): # loops for polling each node
		for x in range(0, 1): # loops for polling each node
			
			i2cBlockData = i2c.read_i2c_block_data(i2cAddr[x], 0x90, 5) # Request: rssi, lap, min, sec, ms
			time.sleep(0.01)

			print "for loop 'x': %d, i2c address: %d" % (x, i2cAddr[x])
			print i2cBlockData
			
	except IOError as e:
		print e
		# i2c = smbus.SMBus(1) # This didn't help
	
	time.sleep(0.01) # main data loop delay
	
db.close()
