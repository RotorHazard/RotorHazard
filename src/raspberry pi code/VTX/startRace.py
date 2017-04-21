#
# Use with the quads on the line ready to start racing
#
# Sets raceStatus to true in the DB and on arduino so that they start counting laps

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
	cursor.execute("UPDATE setup SET raceStatus = 1")
	db.commit()
except:
	db.rollback()

db.close()

# Set clean race start on arduinos, reset laps and raceStatus set true
for x in range(0, numNodes): # loops for polling each node
	i2c.write_i2c_block_data(i2cAddr[x], 0x0A, [0,0,0]) # set arduino lap times to zero
	time.sleep(0.25)
	i2c.write_byte_data(i2cAddr[x], 0x0B, 0) # set arduino lap counter to zero
	time.sleep(0.25)
	i2c.write_byte_data(i2cAddr[x], 0x0E, 1) # set arduino race status to true
	time.sleep(0.25)