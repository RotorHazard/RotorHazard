# VTX Timer by Scott Chin
#
# Use with the quads landed and to stop racing
#
# Sets raceStatus to false in the DB and on arduino so that they stop counting laps

import smbus
import time
import MySQLdb

execfile("/home/pi/VTX/raceBoxConfig.py")

# Start i2c bus
i2c = smbus.SMBus(1)

# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()

sql = "UPDATE setup SET raceStatus = 0 WHERE ID = 1"
try:
	cursor.execute(sql)
	db.commit()
except:
	db.rollback()

db.close()

# raceStatus set false top stop logging laps
for x in range(0, numNodes): # loops for polling each node
	i2c.write_byte_data(i2cAddr[x], 0x0E, 0) # set arduino race status to false
	time.sleep(0.25)