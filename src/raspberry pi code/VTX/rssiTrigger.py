# 
# Takes an i2c address and trigger value then writes to the node and 'nodes' table

import smbus
import time
import MySQLdb
import argparse
import sys


try:
	parser = argparse.ArgumentParser()
	parser.add_argument("address", help="i2c address.", type=int)
	parser.add_argument("rssiTrigger", help="rssi trigger value.", type=int) # rssi trigger value
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
	# Set arduino nodes
	i2c.write_byte_data(args.address, 0x53, args.rssiTrigger) # arduino set rssi threshold
	time.sleep(0.250)
	
	# Insert rssiTriggerThreshold into the database
	try:
		cursor.execute("UPDATE `nodes` SET `rssiTrigger` = %s WHERE `i2cAddr` = %s",(args.rssiTrigger,args.address))
		db.commit()
	except MySQLdb.Error as e:
		print e
		db.rollback()
	except MySQLdb.Warning as e:
		print e
		
except IOError as e:
	print e

db.close()
