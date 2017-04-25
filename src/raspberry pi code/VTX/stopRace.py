#
# Sets race status to false on each node so they stop registering new laps

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
except MySQLdb.Error as e:
	print e
except MySQLdb.Warning as e:
	print e


try:
	cursor.execute("UPDATE `setup` SET `raceStatus` = 0")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

db.close()

# raceStatus set false to stop logging laps
for x in range(0, numNodes): # loops for polling each node
	i2c.write_byte_data(i2cAddr[x], 0x0E, 0) # set arduino race status to false
	time.sleep(0.5)

