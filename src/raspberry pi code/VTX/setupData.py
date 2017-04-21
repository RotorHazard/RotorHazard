#
# Use to clear and setup database then configure arduinos

import smbus
import time
import MySQLdb
import argparse
import sys

try:
	parser = argparse.ArgumentParser()
	parser.add_argument("numNodes", help="Number of nodes.", type=int)
	args = parser.parse_args()
except:
	e = sys.exc_info()[0]
	print e


i2cAddr=[8,10,12,14,16,18]
vtxFreq=[17,25,27,30,21,19] # switch this to human channel values, E2 or 5760MHZ, update on arduino side to match
vtxFreqChan=["E4", "F2", "F4", "F7", "E6", "E2"]


# Start i2c bus
i2c = smbus.SMBus(1)

# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()

# 'setup' table -- empty then fill per config
try:
	cursor.execute("DELETE FROM setup WHERE 1")
	db.commit()
except:
	db.rollback()

try:
	cursor.execute("INSERT INTO setup(commsStatus, raceStatus, minLapTime) VALUES (0,0,5)")
	db.commit()
except:
	db.rollback()

# 'nodes' table -- empty then fill per config
try:
	cursor.execute("DELETE FROM nodes WHERE 1")
	db.commit()
except:
	db.rollback()

for x in range(0, args.numNodes): # adds back nodes ID based on number of nodes
	try:
		cursor.execute("INSERT INTO nodes(node, i2cAddr, vtxFreq, vtxFreqChan, rssi, rssiTrigger) VALUES ('%d','%d','%d','E2',0,0)" % (x+1,i2cAddr[x],vtxFreq[x]))
		db.commit()
	except:
		db.rollback()

# 'currentLaps' table -- empty
try:
	cursor.execute("DELETE FROM currentLaps WHERE 1")
	db.commit()
except:
	db.rollback()
		
# 'currentRace' table -- empty
try:
	cursor.execute("DELETE FROM currentRace WHERE 1")
	db.commit()
except:
	db.rollback()

db.close() # disconnect from server


# Configure and set clean race start on arduinos
for x in range(0, args.numNodes):
	i2c.write_i2c_block_data(i2cAddr[x], 0x0A, [0,0,0]) # set arduino lap times to zero
	time.sleep(0.25)
	i2c.write_byte_data(i2cAddr[x], 0x0B, 0) # set arduino lap counter to zero
	time.sleep(0.25)
	i2c.write_byte_data(i2cAddr[x], 0x0C, 0) # set arduino rssiTriggerThreshold to zero
	time.sleep(0.25)
	i2c.write_byte_data(i2cAddr[x], 0x0D, 5) # set arduino minLapTime as configured, send in seconds, converts to ms on receive
	time.sleep(0.25)
	i2c.write_byte_data(i2cAddr[x], 0x0E, 0) # set arduino race status to false
	time.sleep(0.25)
	i2c.write_byte_data(i2cAddr[x], 0x0F, vtxFreq[0]) # set arduino vtx frequency channel as configured, not implemented on arduino side yet
	time.sleep(0.25)



