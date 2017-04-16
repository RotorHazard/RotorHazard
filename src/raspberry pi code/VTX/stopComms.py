# VTX Timer by Scott Chin
#
# Use to stop communications loop with the arduinos
#
# Maybe this isn't needed at all

import smbus
import time
import MySQLdb

execfile("/home/pi/VTX/stopRace.py")

# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()

db = MySQLdb.connect("localhost","root","delta5fpv","vtx") # Open database connection
cursor = db.cursor() # prepare a cursor object using cursor() method
sql = "UPDATE setup SET commsStatus = 0 WHERE ID = 1"
try:
	cursor.execute(sql) # Execute the SQL command
	db.commit() # Commit your changes in the database
except:
	db.rollback() # Rollback in case there is any error

db.close() # disconnect from server
