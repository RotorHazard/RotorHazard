#
# Populates the 'vtx' database with starting values, configures number of nodes from passed argument value

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


i2cAddr=[8,10,12,14,16,18] # move this to a reference table in the database
vtxNum=[17,25,27,30,21,19] # should use the existing vtx reference table in the database


# Start i2c bus
i2c = smbus.SMBus(1)

# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()

# 'setup' table -- empty then fill per config
try:
	cursor.execute("DELETE FROM `setup` WHERE 1")
	db.commit()
except:
	db.rollback()

try:
	cursor.execute("INSERT INTO `setup` (`commsStatus`, `raceStatus`, `minLapTime`) VALUES (0,0,5)")
	db.commit()
except:
	db.rollback()

# 'nodes' table -- empty then fill per config
try:
	cursor.execute("DELETE FROM `nodes` WHERE 1")
	db.commit()
except:
	db.rollback()

for x in range(0, args.numNodes): # adds back nodes ID based on number of nodes
	try:
		cursor.execute("INSERT INTO `nodes` (`node`, `i2cAddr`, `vtxNum`, `rssi`, `rssiTrigger`) VALUES (%s,%s,%s,0,0)",(x+1,i2cAddr[x],vtxNum[x]))
		db.commit()
	except:
		db.rollback()

# 'currentLaps' table -- empty
try:
	cursor.execute("DELETE FROM `currentLaps` WHERE 1")
	db.commit()
except:
	db.rollback()
		
# 'currentRace' table -- empty
try:
	cursor.execute("DELETE FROM `currentRace` WHERE 1")
	db.commit()
except:
	db.rollback()

# 'vtxReference' table -- empty
try:
	cursor.execute("DELETE FROM `vtxReference` WHERE 1")
	db.commit()
except:
	db.rollback()

try:
	sql = "INSERT INTO `vtxReference` (`vtxNum`, `vtxChan`, `vtxFreq`) VALUES (%s,%s,%s)"
	params = [
		(19,'E4',5645),
		(32,'C1',5658),
		(18,'E3',5665),
		(17,'E2',5685),
		(33,'C2',5695),
		(16,'E1',5705),
		(7,'A8',5725),
		(34,'C3',5732),
		(8,'B1',5733),
		(24,'F1',5740),
		(6,'A7',5745),
		(9,'B2',5752),
		(25,'F2',5760),
		(5,'A6',5765),
		(35,'C4',5769),
		(10,'B3',5771),
		(26,'F3',5780),
		(4,'A5',5785),
		(11,'B4',5790),
		(27,'F4',5800),
		(3,'A4',5805),
		(36,'C5',5806),
		(12,'B5',5809),
		(28,'F5',5820),
		(2,'A3',5825),
		(13,'B6',5828),
		(29,'F6',5840),
		(37,'C6',5843),
		(1,'A2',5845),
		(14,'B7',5847),
		(30,'F7',5860),
		(0,'A1',5865),
		(15,'B8',5866),
		(31,'F8',5880),
		(38,'C7',5880),
		(20,'E5',5885),
		(21,'E6',5905),
		(39,'C8',5917),
		(22,'E7',5925),
		(23,'E8',5945)
	]
	cursor.executemany(sql, params)
	db.commit()
except:
	db.rollback()

	
db.close() # disconnect from server


# Configure and set clean race start on arduinos
for x in range(0, args.numNodes):
	i2c.write_i2c_block_data(i2cAddr[x], 0x0A, [5,vtxNum[0]]) # Zeros all arduino values then sets minLapTime and vtx frequency
	time.sleep(0.5)


