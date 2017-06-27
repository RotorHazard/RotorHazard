# Sets comms status to false to stop the main comms loop

import MySQLdb

# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()

try:
	cursor.execute("UPDATE `status` SET `systemStatus` = 0")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

time.sleep(1.000) # Time for main system loop to read new value

db.close() # disconnect from database
