# Add a new pilot at the next pilot number

import MySQLdb

# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()

# Find next pilot number
try:
	cursor.execute("SELECT MAX(`pilot`) AS `maxPilot` FROM `pilots`")
	maxPilot = cursor.fetchone()
	print maxPilot
	print maxPilot[0]
	db.commit()
except MySQLdb.Error as e:
	print e
except MySQLdb.Warning as e:
	print e

nextPilot = maxPilot[0] + 1

# Add a new pilot at the next number
try:
	cursor.execute("INSERT INTO `pilots` (`pilot`, `callSign`, `name`) VALUES (%s,'newpilot','New Pilot')",(nextPilot))
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

db.close() # disconnect from database
