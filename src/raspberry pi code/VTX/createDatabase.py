#
# Clears the entire 'vtx' database and creates tables and columns new

import MySQLdb


# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()


# 'vtx' database, add code to create database 'vtx' if it doesn't exist


# 'setup' table
try:
	cursor.execute("DROP TABLE IF EXISTS `setup`")
	db.commit()
except MySQLdb.Error:
	print e
	db.rollback()
except MySQLdb.Warning:
	print e

try:
	cursor.execute("""CREATE TABLE IF NOT EXISTS `setup` (`commsStatus` INT, `raceStatus` INT, `minLapTime` INT)""")
	db.commit()
except:
	db.rollback()	

# 'nodes' table
try:
	cursor.execute("DROP TABLE IF EXISTS `nodes`")
	db.commit()
except MySQLdb.Error:
	print e
	db.rollback()
except MySQLdb.Warning:
	print e

try:
	cursor.execute("""CREATE TABLE IF NOT EXISTS `nodes` (`node` INT, `i2cAddr` INT, `vtxNum` INT, `rssi` INT, `rssiTrigger` INT)""")
	db.commit()
except:
	db.rollback()

# 'currentLaps' table
try:
	cursor.execute("DROP TABLE IF EXISTS `currentLaps`")
	db.commit()
except MySQLdb.Error:
	print e
	db.rollback()
except MySQLdb.Warning:
	print e

try:
	cursor.execute("""CREATE TABLE IF NOT EXISTS `currentLaps` (`pilot` INT, `lap` INT, `min` INT, `sec` INT, `milliSec` INT)""")
	db.commit()
except:
	db.rollback()

# 'currentRace' table
try:
	cursor.execute("DROP TABLE IF EXISTS `currentRace`")
	db.commit()
except MySQLdb.Error:
	print e
	db.rollback()
except MySQLdb.Warning:
	print e

try:
	cursor.execute("""CREATE TABLE IF NOT EXISTS `currentRace` (`pilot` INT, `place` INT)""")
	db.commit()
except:
	db.rollback()
	
# 'pilots' table
try:
	cursor.execute("DROP TABLE IF EXISTS `pilots`")
	db.commit()
except MySQLdb.Error:
	print e
	db.rollback()
except MySQLdb.Warning:
	print e

try:
	cursor.execute("""CREATE TABLE IF NOT EXISTS `pilots` (`pilot` INT, `callSign` VARCHAR(255), `firstName` VARCHAR(255), `lastName` VARCHAR(255), `rssiTrigger` INT)""")
	db.commit()
except:
	db.rollback()
	
# 'groups' table
try:
	cursor.execute("DROP TABLE IF EXISTS `groups`")
	db.commit()
except MySQLdb.Error:
	print e
	db.rollback()
except MySQLdb.Warning:
	print e

try:
	cursor.execute("""CREATE TABLE IF NOT EXISTS `groups` (`group` INT, `pilot` INT)""")
	db.commit()
except:
	db.rollback()
	
# 'savedRaces' table
try:
	cursor.execute("DROP TABLE IF EXISTS `savedRaces`")
	db.commit()
except MySQLdb.Error:
	print e
	db.rollback()
except MySQLdb.Warning:
	print e

try:
	cursor.execute("""CREATE TABLE IF NOT EXISTS `savedRaces` (`round` INT, `group` INT, `pilot` INT, `lap` INT, `min` INT, `sec` INT, `milliSec` INT)""")
	db.commit()
except:
	db.rollback()

# 'vtxReference' table
try:
	cursor.execute("DROP TABLE IF EXISTS `vtxReference`")
	db.commit()
except MySQLdb.Error:
	print e
	db.rollback()
except MySQLdb.Warning:
	print e

try:
	cursor.execute("""CREATE TABLE IF NOT EXISTS `vtxReference` (`vtxNum` INT, `vtxChan` VARCHAR(255), `vtxFreq` INT)""")
	db.commit()
except:
	db.rollback()


db.close() # disconnect from server
