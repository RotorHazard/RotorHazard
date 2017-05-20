#
# Populates the 'vtx' database with starting values, configures number of nodes from passed argument value

import smbus
import time
import MySQLdb
import argparse
import sys

# Read in number of nodes from passed argument
try:
	parser = argparse.ArgumentParser()
	parser.add_argument("numNodes", help="Number of nodes.", type=int)
	args = parser.parse_args()
except:
	e = sys.exc_info()[0]
	print e


# This should be read from the i2c bus and the number detected should be compared to the input argument
i2cAddr=[8,10,12,14,16,18]

# Should pass in frequencies or imd5 / imd6 defaults from website?
# This needs to be updated to handle more than 6 nodes
vtxFreq=[5685,5760,5800,5860,5905,5645]
vtxChan=['E2','F2','F4','F7','E6','E4']


# Start i2c bus
i2c = smbus.SMBus(1)

# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()

# Empty 'config' table
try:
	cursor.execute("DELETE FROM `config` WHERE 1")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

# Initialize 'config' table
try:
	cursor.execute("INSERT INTO `config` (`minLapTime`) VALUES (5)")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

# Empty 'status' table
try:
	cursor.execute("DELETE FROM `status` WHERE 1")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

# Initialize 'status' table
try:
	cursor.execute("INSERT INTO `status` (`systemStatus`, `raceStatus`) VALUES (0,0)")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

# Empty 'nodes' table
try:
	cursor.execute("DELETE FROM `nodes` WHERE 1")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e


# Initialize 'nodes' table based on number of nodes
for x in range(0, args.numNodes):
	try:
		cursor.execute("INSERT INTO `nodes` (`node`, `i2cAddr`, `vtxFreq`, `vtxChan`, `rssiTrigger`) VALUES (%s,%s,%s,%s,0)",(x+1,i2cAddr[x],vtxFreq[x],vtxChan[x]))
		db.commit()
	except MySQLdb.Error as e:
		print e
		db.rollback()
	except MySQLdb.Warning as e:
		print e

# Empty 'nodesMem' table
try:
	cursor.execute("DELETE FROM `nodesMem` WHERE 1")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

# Initialize 'nodesMem' table based on number of nodes
for x in range(0, args.numNodes):
	try:
		cursor.execute("INSERT INTO `nodesMem` (`node`, `rssi`, `lapCount`) VALUES (%s,0,0)",(x+1))
		db.commit()
	except MySQLdb.Error as e:
		print e
		db.rollback()
	except MySQLdb.Warning as e:
		print e

# Empty 'currentLaps' table
try:
	cursor.execute("DELETE FROM `currentLaps` WHERE 1")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e


# Empty 'vtxReference' table
try:
	cursor.execute("DELETE FROM `vtxReference` WHERE 1")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

# Initialize 'vtxReference' table
try:
	sql = "INSERT INTO `vtxReference` (`vtxChan`, `vtxFreq`) VALUES (%s,%s)"
	params = [
		('E4',5645),
		('C1',5658),
		('E3',5665),
		('E2',5685),
		('C2',5695),
		('E1',5705),
		('A8',5725),
		('C3',5732),
		('B1',5733),
		('F1',5740),
		('A7',5745),
		('B2',5752),
		('F2',5760),
		('A6',5765),
		('C4',5769),
		('B3',5771),
		('F3',5780),
		('A5',5785),
		('B4',5790),
		('F4',5800),
		('A4',5805),
		('C5',5806),
		('B5',5809),
		('F5',5820),
		('A3',5825),
		('B6',5828),
		('F6',5840),
		('C6',5843),
		('A2',5845),
		('B7',5847),
		('F7',5860),
		('A1',5865),
		('B8',5866),
		('F8',5880),
		('C7',5880),
		('E5',5885),
		('E6',5905),
		('C8',5917),
		('E7',5925),
		('E8',5945)
	]
	cursor.executemany(sql, params)
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

	
db.close() # disconnect from database


# Initialize arduinos
for x in range(0, args.numNodes):
	partA = (vtxFreq[x] >> 8) # Split vtxFreq into two bytes to send
	partB = (vtxFreq[x] & 0xFF)
	i2c.write_i2c_block_data(i2cAddr[x], 0x51, [partA, partB]) # Initialize arduino defaults and set vtx frequency
	time.sleep(0.250)