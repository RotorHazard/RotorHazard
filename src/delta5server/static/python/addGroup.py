# Add a new group at the next group number

import MySQLdb

# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()

# Find next group number
try:
	cursor.execute("SELECT MAX(`group`) AS `maxGroup` FROM `groups`")
	maxGroup = cursor.fetchone()
	db.commit()
except MySQLdb.Error as e:
	print e
except MySQLdb.Warning as e:
	print e

nextGroup = maxGroup[0] + 1

# Get group 1 data as an example and insert into next group
try:
	cursor.execute("SELECT `node`, `vtxChan` FROM `groups` WHERE `group` = 1")
	results = cursor.fetchall() # Fetch all the rows in a list of lists
	index = 0
	for row in results:
		index += 1
		cursor.execute("INSERT INTO `groups` (`group`, `node`, `pilot`, `vtxChan`, `rssiTrigger`) VALUES (%s,%s,%s,%s,0)",(nextGroup,row[0],index,row[1]))
	db.commit()
except MySQLdb.Error as e:
	print e
except MySQLdb.Warning as e:
	print e

db.close() # disconnect from database
