# 
# Takes an group number, node number, and vtx channel then writes to the database and node if needed

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
	parser.add_argument("vtxChan", help="vtx channel", type=str) # vtx channel and frequency as a string
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
	# Update node channel
	try:
		vtxFrequency = int(args.vtxChan.split()[1]) # Splits on spaces and gets the mhz number
		partA = (vtxFrequency >> 8)
		partB = (vtxFrequency & 0xFF)
		i2c.write_i2c_block_data(i2cAddr, 0x56, [partA, partB]) # Set vtx frequency
		time.sleep(0.250)
	except IOError as e:
		print e
	
# Update database channel
try:
	cursor.execute("UPDATE `groups` SET `vtxChan` = %s WHERE `group` = %s AND `node` = %s",(args.vtxChan,args.group,args.node))
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

db.close()
