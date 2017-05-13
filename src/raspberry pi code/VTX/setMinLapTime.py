# 
# Takes a min lap time number in seconds and writes to all nodes and the 'setup' table

import smbus
import time
import MySQLdb
import argparse
import sys


try:
	parser = argparse.ArgumentParser()
	parser.add_argument("minLapTime", help="min lap time.", type=int)
	args = parser.parse_args()
except:
	e = sys.exc_info()[0]
	print e

# start i2c bus
i2c = smbus.SMBus(1)

# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()


# Get nodes info
i2cAddr = []
try:
	cursor.execute("SELECT * FROM `nodes`")
	numNodes = int(cursor.rowcount)
	print "numNodes: %d" % numNodes
	for x in range(0, numNodes):
		row = cursor.fetchone()
		print row
		i2cAddr.append(int(row[1]))
	print "i2cAddr: "
	print i2cAddr
except MySQLdb.Error as e:
	print e
except MySQLdb.Warning as e:
	print e


try:
	# Set arduino nodes
	for x in range(0, numNodes): # loops for polling each node
		i2c.write_byte_data(i2cAddr[x], 0x54, args.minLapTime) # Set min lap time in seconds
		time.sleep(0.250)
	
	# Insert min lap time into the database
	try:
		cursor.execute("UPDATE `setup` SET `minLapTime` = %s",(args.minLapTime))
		db.commit()
	except MySQLdb.Error as e:
		print e
		db.rollback()
	except MySQLdb.Warning as e:
		print e
		
except IOError as e:
	print e

db.close()
