# Saves the currentLaps table to the savedRaces table, needs updates when groups are added

import MySQLdb

# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()

# Get the current group number
try:
	cursor.execute("SELECT `group` FROM `config`")
	results = cursor.fetchone()
	currentGroup = results[0]
	print "current group:"
	print currentGroup
	db.commit()
except MySQLdb.Error as e:
	print e
except MySQLdb.Warning as e:
	print e

# Find next race number
try:
	cursor.execute("SELECT MAX(`race`) AS `maxRace` FROM `savedRaces` WHERE `group` = %s",(currentGroup))
	results = cursor.fetchone()
	maxRace = results[0]
	print "max race:"
	print maxRace
	if maxRace is None:
		nextRace = 1
	else:
		nextRace = maxRace + 1
	print "next race:"
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
	cursor.execute("UPDATE `savedRaces` SET `race` = %s, `group` = %s WHERE IFNULL(`race`,0) = 0",(nextRace,currentGroup))
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

db.close() # disconnect from database
