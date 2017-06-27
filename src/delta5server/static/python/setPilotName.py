# Takes an group number, node number, and vtx channel then writes to the database and node if needed

import MySQLdb
import argparse
import sys

# Read in arguments
try:
	parser = argparse.ArgumentParser()
	parser.add_argument("pilot", help="pilot number", type=int)
	parser.add_argument("name", help="new pilot name", type=str)
	args = parser.parse_args()
except:
	e = sys.exc_info()[0]
	print e

# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()
	
# Update pilot in database
try:
	cursor.execute("UPDATE `pilots` SET `name` = %s WHERE `pilot` = %s",(args.name,args.pilot))
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

db.close() # disconnect from database
