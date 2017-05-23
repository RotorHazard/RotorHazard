# Saves the currentLaps table to the savedRaces table, needs updates when groups are added

import MySQLdb

# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()

# Find next race number
try:
	cursor.execute("SELECT MAX(`race`) AS `maxRace` FROM `savedRaces`")
	results = cursor.fetchall()
	for row in results:
		print row[0]
		if row[0] is None:
			nextRace = 1
		else:
			nextRace = row[0]+1
		print nextRace
	db.commit()
except MySQLdb.Error as e:
	print e
except MySQLdb.Warning as e:
	print e
	
# Move Data
# `currentLaps` (`pilot`, `lap`, `min`, `sec`, `milliSec`)
# `savedRaces` (`race`, `group`, `pilot`, `lap`, `min`, `sec`, `milliSec`)
try:
	cursor.execute("INSERT INTO `savedRaces` (`pilot`, `lap`, `min`, `sec`, `milliSec`) SELECT * FROM `currentLaps`")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

# Update empty race and group fields
try:
	cursor.execute("UPDATE `savedRaces` SET `race` = %s, `group` = 1 WHERE IFNULL(`race`,0) = 0",nextRace)
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

db.close() # disconnect from database
