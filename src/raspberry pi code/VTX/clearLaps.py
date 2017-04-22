#
# Use after all the laps data has been recorded 
#
# Removes all laps from the database races table

import MySQLdb

# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()

try:
	cursor.execute("TRUNCATE TABLE `currentLaps`")
	db.commit()
except:
	db.rollback()

db.close()