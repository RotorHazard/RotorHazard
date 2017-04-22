#
# Use to stop communications loop with the arduinos
#
# Maybe this isn't needed at all

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
