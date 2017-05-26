# Changes the current group from passed argument

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

# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()

# Update current group variable in database
try:
	cursor.execute("UPDATE `config` SET `group` = %s",(args.newGroup))
	db.commit()
except MySQLdb.Error as e:
	print e
except MySQLdb.Warning as e:
	print e

db.close() # disconnect from database
