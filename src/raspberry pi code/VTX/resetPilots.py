# Populates the 'vtx' database with starting values, configures number of nodes from passed argument value

import MySQLdb

# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()

# Initialize 'groups' table -- This should be generated from the number of nodes passed in!!!
try:
	cursor.execute("TRUNCATE TABLE `pilots`")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e
try:
	cursor.execute("INSERT INTO `pilots` (`pilot`, `callSign`, `name`) VALUES (0,'','')")
	cursor.execute("INSERT INTO `pilots` (`pilot`, `callSign`, `name`) VALUES (1,'pilot1','Pilot One')")
	cursor.execute("INSERT INTO `pilots` (`pilot`, `callSign`, `name`) VALUES (2,'pilot2','Pilot Two')")
	cursor.execute("INSERT INTO `pilots` (`pilot`, `callSign`, `name`) VALUES (3,'pilot3','Pilot Three')")
	cursor.execute("INSERT INTO `pilots` (`pilot`, `callSign`, `name`) VALUES (4,'pilot4','Pilot Four')")
	cursor.execute("INSERT INTO `pilots` (`pilot`, `callSign`, `name`) VALUES (5,'pilot5','Pilot Five')")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

db.close() # disconnect from database
