#
# Use with the quads landed and to stop racing
#
# Sets raceStatus to false in the DB and on arduino so that they stop counting laps

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
vtxFreq = []
try:
	cursor.execute("SELECT * FROM nodes");
	numNodes = int(cursor.rowcount)
	print "numNodes: %d" % numNodes
	for x in range(0, numNodes):
		row = cursor.fetchone()
		print row
		i2cAddr.append(int(row[1]))
		vtxFreq.append(int(row[2]))
	print "i2cAddr: "
	print i2cAddr
	print "vtxFreq: "
	print vtxFreq
except:
	print "Error: unable to fetch data"


try:
	cursor.execute("UPDATE setup SET raceStatus = 0")
	db.commit()
except:
	db.rollback()

db.close()

# raceStatus set false top stop logging laps
for x in range(0, numNodes): # loops for polling each node
	i2c.write_byte_data(i2cAddr[x], 0x0E, 0) # set arduino race status to false
	time.sleep(0.25)