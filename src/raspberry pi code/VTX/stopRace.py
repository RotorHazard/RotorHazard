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
