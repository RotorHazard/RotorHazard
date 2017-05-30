# Resets variables on each node then sets race status to true

import smbus
import time
import MySQLdb

# Start i2c bus
i2c = smbus.SMBus(1)

# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()

# Get node i2cAddr info
i2cAddr = []
try:
	cursor.execute("SELECT * FROM `nodes`") # Update to remove * and just get i2cAddr
	numNodes = int(cursor.rowcount)
	print "numNodes: %d" % numNodes
	for x in range(0, numNodes):
		row = cursor.fetchone()
		print row
		i2cAddr.append(int(row[1]))
	print "i2cAddr: "
	print i2cAddr
except MySQLdb.Error as e:
	print e
except MySQLdb.Warning as e:
	print e

# Reset all lapCount to 0
try:
	cursor.execute("UPDATE `nodesMem` SET `lapCount` = 0")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

# Set raceStatus to true
try:
	cursor.execute("UPDATE `status` SET `raceStatus` = 1")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

db.close() # disconnect from database

# Set clean race start on arduinos, reset laps and raceStatus set true
for x in range(0, numNodes): # loops for polling each node
	i2c.write_byte(i2cAddr[x], 0x52) # race reset, raceStatus to 1
	time.sleep(0.250)
