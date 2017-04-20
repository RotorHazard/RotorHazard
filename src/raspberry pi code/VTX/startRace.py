# VTX Timer by Scott Chin
#
# Use with the quads on the line ready to start racing
#
# Sets raceStatus to true in the DB and on arduino so that they start counting laps

import smbus
import time
import MySQLdb

execfile("/home/pi/VTX/raceBoxConfig.py")

# Start i2c bus
i2c = smbus.SMBus(1)

# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()

sql = "UPDATE setup SET raceStatus = 1 WHERE ID = 1"
try:
	cursor.execute(sql)
	db.commit()
except:
	db.rollback()
db.close()

# Set clean race start on arduinos, reset laps and raceStatus set true
for x in range(0, numNodes): # loops for polling each node
	i2c.write_i2c_block_data(i2cAddr[x], 0x0A, [0,0,0]) # set arduino lap times to zero
	time.sleep(0.1)
	i2c.write_byte_data(i2cAddr[x], 0x0B, 0) # set arduino lap counter to zero
	time.sleep(0.1)
	i2c.write_byte_data(i2cAddr[x], 0x0E, 1) # set arduino race status to true
	time.sleep(0.1)