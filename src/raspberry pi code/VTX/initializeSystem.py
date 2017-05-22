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
vtxChan=['E2 5685','F2 5760','F4 5800','F7 5860','E6 5905','E4 5645']

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
	cursor.execute("INSERT INTO `config` (`group`,`minLapTime`) VALUES (1,5)")
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
		cursor.execute("INSERT INTO `nodes` (`node`, `i2cAddr`) VALUES (%s,%s)",(x+1,i2cAddr[x]))
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

# Empty 'pilots' table
try:
	cursor.execute("DELETE FROM `pilots` WHERE 1")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

# Load pilots for group 1 -- This should be generated from the number of nodes passed in!!!
try:
	cursor.execute("INSERT INTO `pilots` (`pilot`, `callSign`, `name`) VALUES (0,'','')")
	cursor.execute("INSERT INTO `pilots` (`pilot`, `callSign`, `name`) VALUES (1,'pilot1','Pilot One')")
	cursor.execute("INSERT INTO `pilots` (`pilot`, `callSign`, `name`) VALUES (2,'pilot2','Pilot Two')")
	cursor.execute("INSERT INTO `pilots` (`pilot`, `callSign`, `name`) VALUES (3,'pilot3','Pilot Three')")
	cursor.execute("INSERT INTO `pilots` (`pilot`, `callSign`, `name`) VALUES (4,'pilot4','Pilot Four')")
	cursor.execute("INSERT INTO `pilots` (`pilot`, `callSign`, `name`) VALUES (5,'pilot5','Pilot Five')")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

# Empty 'groups' table
try:
	cursor.execute("DELETE FROM `groups` WHERE 1")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

# Load pilots for group 1 -- This should be generated from the number of nodes passed in!!!
try:
	cursor.execute("INSERT INTO `groups` (`group`, `node`, `pilot`, `vtxChan`, `rssiTrigger`) VALUES (1,1,1,'E2 5685',0)")
	cursor.execute("INSERT INTO `groups` (`group`, `node`, `pilot`, `vtxChan`, `rssiTrigger`) VALUES (1,2,2,'F2 5760',0)")
	cursor.execute("INSERT INTO `groups` (`group`, `node`, `pilot`, `vtxChan`, `rssiTrigger`) VALUES (1,3,3,'F4 5800',0)")
	cursor.execute("INSERT INTO `groups` (`group`, `node`, `pilot`, `vtxChan`, `rssiTrigger`) VALUES (1,4,4,'F7 5860',0)")
	cursor.execute("INSERT INTO `groups` (`group`, `node`, `pilot`, `vtxChan`, `rssiTrigger`) VALUES (1,5,5,'E6 5905',0)")
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
	sql = "INSERT INTO `vtxReference` (`vtxChan`) VALUES (%s)"
	params = [
		('E4 5645'),
		('C1 5658'),
		('E3 5665'),
		('E2 5685'),
		('C2 5695'),
		('E1 5705'),
		('A8 5725'),
		('C3 5732'),
		('B1 5733'),
		('F1 5740'),
		('A7 5745'),
		('B2 5752'),
		('F2 5760'),
		('A6 5765'),
		('C4 5769'),
		('B3 5771'),
		('F3 5780'),
		('A5 5785'),
		('B4 5790'),
		('F4 5800'),
		('A4 5805'),
		('C5 5806'),
		('B5 5809'),
		('F5 5820'),
		('A3 5825'),
		('B6 5828'),
		('F6 5840'),
		('C6 5843'),
		('A2 5845'),
		('B7 5847'),
		('F7 5860'),
		('A1 5865'),
		('B8 5866'),
		('F8 5880'),
		('C7 5880'),
		('E5 5885'),
		('E6 5905'),
		('C8 5917'),
		('E7 5925'),
		('E8 5945')
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
	vtxFreq = int(vtxChan[x].split()[1])
	partA = (vtxFreq >> 8) # Split vtxFreq into two bytes to send
	partB = (vtxFreq & 0xFF)
	i2c.write_i2c_block_data(i2cAddr[x], 0x51, [partA, partB]) # Initialize arduino defaults and set vtx frequency
	time.sleep(0.250)