# Takes an group number, node number, and trigger value then writes to the database and node if needed

import smbus
import time
import MySQLdb
import argparse
import sys

# Read in arguments
try:
	parser = argparse.ArgumentParser()
	parser.add_argument("group", help="group number", type=int)
	parser.add_argument("node", help="node number", type=int)
	parser.add_argument("rssiTrigger", help="rssi trigger", type=int)
	args = parser.parse_args()
except:
	e = sys.exc_info()[0]
	print e

# start i2c bus
i2c = smbus.SMBus(1)

# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()

# Get current group
try:
	cursor.execute("SELECT `group` FROM `config`")
	result = cursor.fetchone() # Fetch all the rows in a list of lists
	currentGroup = result[0]
	print "Current group: %d" % (currentGroup)
except MySQLdb.Error as e:
	print e
except MySQLdb.Warning as e:
	print e

# If the group to update is the same as the current group then update the arduino node
if args.group == currentGroup:
	# Get the i2c address of the node
	try:
		cursor.execute("SELECT `i2cAddr` FROM `nodes` WHERE `node` = %s",(args.node))
		result = cursor.fetchone() # Fetch all the rows in a list of lists
		i2cAddr = result[0]
		print "i2cAddr: %d" % (i2cAddr)
	except MySQLdb.Error as e:
		print e
	except MySQLdb.Warning as e:
		print e
	
	# Update node rssi trigger value
	try:
		i2c.write_byte_data(i2cAddr, 0x53, args.rssiTrigger) # Arduino set rssi threshold
		time.sleep(0.250)
	except IOError as e:
		print e

# Update database rssi trigger value
try:
	cursor.execute("UPDATE `groups` SET `rssiTrigger` = %s WHERE `group` = %s AND `node` = %s",(args.rssiTrigger,args.group,args.node))
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

db.close() # Disconnect from database
