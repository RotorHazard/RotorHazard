# Populates the 'vtx' database with starting values, configures number of nodes from passed argument value

import MySQLdb

# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()

# Initialize 'groups' table -- This should be generated from the number of nodes passed in!!!
try:
	cursor.execute("TRUNCATE TABLE `groups`")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e
try:
	cursor.execute("INSERT INTO `groups` (`group`, `node`, `pilot`, `vtxChan`, `rssiTrigger`) VALUES (1,1,1,'E2 5685',0)")
	cursor.execute("INSERT INTO `groups` (`group`, `node`, `pilot`, `vtxChan`, `rssiTrigger`) VALUES (1,2,2,'F2 5760',0)")
	cursor.execute("INSERT INTO `groups` (`group`, `node`, `pilot`, `vtxChan`, `rssiTrigger`) VALUES (1,3,3,'F4 5800',0)")
	cursor.execute("INSERT INTO `groups` (`group`, `node`, `pilot`, `vtxChan`, `rssiTrigger`) VALUES (1,4,4,'F7 5860',0)")
	cursor.execute("INSERT INTO `groups` (`group`, `node`, `pilot`, `vtxChan`, `rssiTrigger`) VALUES (1,5,5,'E6 5905',0)")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

db.close() # disconnect from database
