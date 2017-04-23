#
# Sets comms status to false to stop the main comms loop

import MySQLdb


# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()

try:
	cursor.execute("UPDATE `setup` SET `commsStatus` = 0")
	db.commit()
except:
	db.rollback()

db.close()
