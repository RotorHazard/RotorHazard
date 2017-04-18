# VTX Timer by Scott Chin
#
# Use to clear and setup database then configure arduinos

import smbus
import time
import MySQLdb

execfile("/home/pi/VTX/raceBoxConfig.py")

# Start i2c bus
i2c = smbus.SMBus(1)

# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()

# 'setup' table -- empty then fill per config
sql = "DELETE FROM `setup` WHERE 1"
try:
	cursor.execute(sql)
	db.commit()
except:
	db.rollback()

sql = "INSERT INTO `setup`(`ID`, `commsStatus`, `raceStatus`, `minLapTime`) VALUES (1,0,0,5000)"
try:
	cursor.execute(sql)
	db.commit()
except:
	db.rollback()

# 'nodes' table -- empty then fill per config
sql = "DELETE FROM `nodes` WHERE 1"
try:
	cursor.execute(sql)
	db.commit()
except:
	db.rollback()

for x in range(0, numNodes): # adds back nodes ID based on number of nodes
	sql = "INSERT INTO `nodes`(`ID`, `channel`, `rssi`, `rssiTrig`) VALUES ('%d','%d',0,0)" % (x+1,vtxFreq[x])
	try:
		cursor.execute(sql)
		db.commit()
	except:
		db.rollback()

# 'races' table -- empty
sql = "DELETE FROM `races` WHERE 1"
try:
	cursor.execute(sql)
	db.commit()
except:
	db.rollback()

db.close() # disconnect from server


# Configure and set clean race start on arduinos
for x in range(0, numNodes):
	i2c.write_i2c_block_data(i2cAddr[x], 0x0A, [0,0,0]) # set arduino lap times to zero
	time.sleep(0.1)
	i2c.write_byte_data(i2cAddr[x], 0x0B, 0) # set arduino lap counter to zero
	time.sleep(0.1)
	i2c.write_byte_data(i2cAddr[x], 0x0C, 0) # set arduino rssiTriggerThreshold to zero
	time.sleep(0.1)
	i2c.write_byte_data(i2cAddr[x], 0x0D, (5000/1000)) # set arduino minLapTime as configured, convert to s, then back to ms on receive
	time.sleep(0.1)
	i2c.write_byte_data(i2cAddr[x], 0x0E, 0) # set arduino race status to false
	time.sleep(0.1)
	i2c.write_byte_data(i2cAddr[x], 0x0F, vtxFreq[0]) # set arduino vtx frequency channel as configured, not implemented on arduino side yet
	time.sleep(0.1)



