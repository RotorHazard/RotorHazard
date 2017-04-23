#
# Clears the currentLaps table to get ready for a new race

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