#
# Resets variables on each node then sets race status to true

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
	cursor.execute("SELECT * FROM `nodes`")
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
	cursor.execute("UPDATE `nodes` SET `lapCount` = 0")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

# Set raceStatus to true for web display
try:
	cursor.execute("UPDATE `setup` SET `raceStatus` = 1")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

db.close()

# Set clean race start on arduinos, reset laps and raceStatus set true
for x in range(0, numNodes): # loops for polling each node
	i2c.write_byte(i2cAddr[x], 0x52) # race reset, raceStatus to 1
	time.sleep(0.250)


