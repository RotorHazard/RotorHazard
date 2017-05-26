# Updates the pilot in a group

import MySQLdb
import argparse
import sys

# Read in arguments
try:
	parser = argparse.ArgumentParser()
	parser.add_argument("group", help="group number", type=int)
	parser.add_argument("node", help="node number", type=int)
	parser.add_argument("pilot", help="pilot number", type=int)
	args = parser.parse_args()
except:
	e = sys.exc_info()[0]
	print e

# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()

# Update database channel only
try:
	cursor.execute("UPDATE `groups` SET `pilot` = %s WHERE `group` = %s AND `node` = %s",(args.pilot,args.group,args.node))
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

db.close() # disconnect from database
