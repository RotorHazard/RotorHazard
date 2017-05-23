# Populates the 'vtx' database with test data

import MySQLdb

# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()

# Load 'currentLaps' table
try:
	cursor.execute("DELETE FROM `currentLaps` WHERE 1")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e
try:
	cursor.execute("INSERT INTO `currentLaps` (`pilot`, `lap`, `min`, `sec`, `milliSec`) VALUES (1,1,0,10,510)")
	cursor.execute("INSERT INTO `currentLaps` (`pilot`, `lap`, `min`, `sec`, `milliSec`) VALUES (2,1,0,8,510)")
	cursor.execute("INSERT INTO `currentLaps` (`pilot`, `lap`, `min`, `sec`, `milliSec`) VALUES (3,1,0,9,612)")
	cursor.execute("INSERT INTO `currentLaps` (`pilot`, `lap`, `min`, `sec`, `milliSec`) VALUES (1,2,0,10,5)")
	cursor.execute("INSERT INTO `currentLaps` (`pilot`, `lap`, `min`, `sec`, `milliSec`) VALUES (2,2,0,8,12)")
	cursor.execute("INSERT INTO `currentLaps` (`pilot`, `lap`, `min`, `sec`, `milliSec`) VALUES (3,2,0,9,754)")
	cursor.execute("INSERT INTO `currentLaps` (`pilot`, `lap`, `min`, `sec`, `milliSec`) VALUES (2,3,0,8,855)")
	cursor.execute("INSERT INTO `currentLaps` (`pilot`, `lap`, `min`, `sec`, `milliSec`) VALUES (3,3,0,9,44)")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

# Edit 'pilots' table with actual names
try:
	cursor.execute("UPDATE `pilots` SET `callSign` = %s, `name` = %s WHERE `pilot` = %s",('howflyquad','Alex',1))
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

# Add group 2 pilots
try:
	cursor.execute("INSERT INTO `pilots` (`pilot`, `callSign`, `name`) VALUES (6,'group2-1','Group2 One')")
	cursor.execute("INSERT INTO `pilots` (`pilot`, `callSign`, `name`) VALUES (7,'group2-2','Group2 Two')")
	cursor.execute("INSERT INTO `pilots` (`pilot`, `callSign`, `name`) VALUES (8,'group2-3','Group2 Three')")
	cursor.execute("INSERT INTO `pilots` (`pilot`, `callSign`, `name`) VALUES (9,'group2-4','Group2 Four')")
	cursor.execute("INSERT INTO `pilots` (`pilot`, `callSign`, `name`) VALUES (10,'group2-5','Group2 Five')")
	cursor.execute("INSERT INTO `groups` (`group`, `node`, `pilot`, `vtxChan`, `rssiTrigger`) VALUES (2,1,6,'E2 5685',0)")
	cursor.execute("INSERT INTO `groups` (`group`, `node`, `pilot`, `vtxChan`, `rssiTrigger`) VALUES (2,2,7,'F2 5760',0)")
	cursor.execute("INSERT INTO `groups` (`group`, `node`, `pilot`, `vtxChan`, `rssiTrigger`) VALUES (2,3,8,'F4 5800',0)")
	cursor.execute("INSERT INTO `groups` (`group`, `node`, `pilot`, `vtxChan`, `rssiTrigger`) VALUES (2,4,9,'F7 5860',0)")
	cursor.execute("INSERT INTO `groups` (`group`, `node`, `pilot`, `vtxChan`, `rssiTrigger`) VALUES (2,5,10,'E6 5905',0)")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

db.close() # disconnect from database
