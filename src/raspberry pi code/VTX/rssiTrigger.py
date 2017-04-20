# VTX Timer by Scott Chin
# This file will set the trigger threshold on the arduino with command 0x81
# It returns the data in an array with [rssiTrig]

import smbus
import time
import MySQLdb
import argparse
import sys

try:
	parser = argparse.ArgumentParser()
	parser.add_argument("node", help="Node number.", type=int)
	parser.add_argument("address", help="i2c address.", type=int)
	parser.add_argument("action", help="rssiTrigger action.", type=str) # set, inc, dec
	args = parser.parse_args()
except:
	e = sys.exc_info()[0]
	print e

# start i2c bus
i2c = smbus.SMBus(1)

# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()


try:
	if args.action == 'set':
		i2cBlockData = i2c.read_i2c_block_data(args.address, 0x81, 1) # arduino setRssiThreshold() and return
		time.sleep(0.1)
	elif  args.action == 'inc':
		i2cBlockData = i2c.read_i2c_block_data(args.address, 0x82, 1) # arduino rssiTriggerThreshold plus 5 and return
		time.sleep(0.1)
	elif  args.action == 'dec':
		i2cBlockData = i2c.read_i2c_block_data(args.address, 0x83, 1) # arduino rssiTriggerThreshold minus 5 and return
		time.sleep(0.1)
	
	# Insert rssiTriggerThreshold into the database
	sql = "UPDATE nodes SET rssiTrig = '%d' WHERE ID = '%d'" % (i2cBlockData[0],args.node)
	try:
		cursor.execute(sql)
		db.commit()
	except:
		db.rollback()
	
	time.sleep(0.1)
except IOError as e:
	print e

db.close()
