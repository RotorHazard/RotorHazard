#
# Saves the currentLaps table to the savedRaces table, needs updates when groups are added

import MySQLdb


# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()

# Find next round number
try:
	cursor.execute("SELECT MAX(`round`) AS `maxRound` FROM `savedRaces`")
	results = cursor.fetchall()
	for row in results:
		print row[0]
		if row[0] is None:
			nextRound = 1
		else:
			nextRound = row[0]+1
		print nextRound
	db.commit()
except MySQLdb.Error as e:
	print e
except MySQLdb.Warning as e:
	print e
	
# Move Data
# `currentLaps` (`pilot`, `lap`, `min`, `sec`, `milliSec`)
# `savedRaces` (`round`, `group`, `pilot`, `lap`, `min`, `sec`, `milliSec`)
try:
	cursor.execute("INSERT INTO `savedRaces` (`pilot`, `lap`, `min`, `sec`, `milliSec`) SELECT * FROM `currentLaps`")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

# Update missing fields
try:
	cursor.execute("UPDATE `savedRaces` SET `round` = %s, `group` = 1 WHERE IFNULL(`round`,0) = 0",nextRound)
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e


db.close()