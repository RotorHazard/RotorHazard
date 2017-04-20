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

sql = "UPDATE setup SET commsStatus = 0 WHERE ID = 1"
try:
	cursor.execute(sql)
	db.commit()
except:
	db.rollback()

db.close()
