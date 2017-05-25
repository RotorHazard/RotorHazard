# Populates the 'vtx' database with starting values, configures number of nodes from passed argument value

import smbus
import time
import MySQLdb
import argparse
import sys

# Read in the new group number from passed argument
try:
	parser = argparse.ArgumentParser()
	parser.add_argument("newGroup", help="new group to switch to", type=int)
	args = parser.parse_args()
except:
	e = sys.exc_info()[0]
	print e

# Start i2c bus
i2c = smbus.SMBus(1)

# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()

# Get i2c addresses from database
i2cAddr = []
try:
	cursor.execute("SELECT `i2cAddr` FROM `nodes`")
	numNodes = int(cursor.rowcount) # Get the number of nodes in the system from the size of nodes table
	results = cursor.fetchall() # Fetch all the rows in a list of lists
	for row in results:
		i2cAddr.append(int(row[0]))
except MySQLdb.Error as e:
	print e
except MySQLdb.Warning as e:
	print e

# Get vtx channels of new group from database
vtxChan = []
try:
	cursor.execute("SELECT `vtxChan` FROM `groups` WHERE `group` = %s",(args.newGroup))
	results = cursor.fetchall() # Fetch all the rows in a list of lists
	for row in results:
		vtxChan.append(row[0])
except MySQLdb.Error as e:
	print e
except MySQLdb.Warning as e:
	print e

# Update current group variable in database
try:
	cursor.execute("UPDATE `config` SET `group` = %s",(args.newGroup))
	db.commit()
except MySQLdb.Error as e:
	print e
except MySQLdb.Warning as e:
	print e

db.close() # disconnect from database

# Initialize arduinos
for x in range(0, numNodes):
	vtxFreq = int(vtxChan[x].split()[1])
	partA = (vtxFreq >> 8) # Split vtxFreq into two bytes to send
	partB = (vtxFreq & 0xFF)
	i2c.write_i2c_block_data(i2cAddr[x], 0x51, [partA, partB]) # Initialize arduino defaults and set vtx frequency
	time.sleep(0.250)
