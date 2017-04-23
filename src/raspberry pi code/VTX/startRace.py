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
	cursor.execute("SELECT * FROM `nodes`");
	numNodes = int(cursor.rowcount)
	print "numNodes: %d" % numNodes
	for x in range(0, numNodes):
		row = cursor.fetchone()
		print row
		i2cAddr.append(int(row[1]))
	print "i2cAddr: "
	print i2cAddr
except:
	print "Error: unable to fetch data"


# Should clear laps from current race here


try:
	cursor.execute("UPDATE `setup` SET `raceStatus` = 1")
	db.commit()
except:
	db.rollback()

db.close()

# Set clean race start on arduinos, reset laps and raceStatus set true
for x in range(0, numNodes): # loops for polling each node
	i2c.write_byte_data(i2cAddr[x], 0x0B, 0) # race reset, set lap, min, sec, ms, lastLapTime to 0, raceStatus to 1
	time.sleep(0.5)


