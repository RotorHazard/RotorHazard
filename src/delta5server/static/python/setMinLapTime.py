# Takes a min lap time number in seconds and writes to the database

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

# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()

# Insert min lap time into the database
try:
	cursor.execute("UPDATE `config` SET `minLapTime` = %s",(args.minLapTime))
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

db.close() # disconnect from database
