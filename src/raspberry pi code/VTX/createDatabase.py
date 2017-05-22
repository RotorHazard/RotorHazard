#
# Clears the entire 'vtx' database and creates tables and columns new

import MySQLdb


# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()


# 'vtx' database, add code to create database 'vtx' if it doesn't exist


# 'config' table - Stores system configuration variables
try:
	cursor.execute("DROP TABLE IF EXISTS `config`")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

try:
	cursor.execute("""CREATE TABLE IF NOT EXISTS `config` (`group` INT, `minLapTime` INT)""")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e	

# 'status' table - Volitile MEMORY table for frequently changing system variables
try:
	cursor.execute("DROP TABLE IF EXISTS `status`")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

try:
	cursor.execute("""CREATE TABLE IF NOT EXISTS `status` (`systemStatus` INT, `raceStatus` INT) ENGINE = MEMORY""")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

# 'nodes' table - Stores node configuration
try:
	cursor.execute("DROP TABLE IF EXISTS `nodes`")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

try:
	cursor.execute("""CREATE TABLE IF NOT EXISTS `nodes` (`node` INT, `i2cAddr` INT)""")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

# 'nodesMem' table - Volitile MEMORY table for frequently changing node data
try:
	cursor.execute("DROP TABLE IF EXISTS `nodesMem`")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

try:
	cursor.execute("""CREATE TABLE IF NOT EXISTS `nodesMem` (`node` INT, `rssi` INT, `lapCount` INT) ENGINE = MEMORY""")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

# 'currentLaps' table - Stores completed lap data for the current race to be moved to savedRaces later or cleared
try:
	cursor.execute("DROP TABLE IF EXISTS `currentLaps`")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

try:
	cursor.execute("""CREATE TABLE IF NOT EXISTS `currentLaps` (`pilot` INT, `lap` INT, `min` INT, `sec` INT, `milliSec` INT)""")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e
	
# 'pilots' table
try:
	cursor.execute("DROP TABLE IF EXISTS `pilots`")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

try:
	cursor.execute("""CREATE TABLE IF NOT EXISTS `pilots` (`pilot` INT, `callSign` VARCHAR(255), `name` VARCHAR(255))""")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

# 'groups' table
try:
	cursor.execute("DROP TABLE IF EXISTS `groups`")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

try:
	cursor.execute("""CREATE TABLE IF NOT EXISTS `groups` (`group` INT, `node` INT, `pilot` INT, `vtxChan` VARCHAR(10), `rssiTrigger` INT)""")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e
	
# 'savedRaces' table - Stores all the races and laps data for the current session
try:
	cursor.execute("DROP TABLE IF EXISTS `savedRaces`")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

try:
	cursor.execute("""CREATE TABLE IF NOT EXISTS `savedRaces` (`race` INT, `group` INT, `pilot` INT, `lap` INT, `min` INT, `sec` INT, `milliSec` INT)""")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

# 'vtxReference' table - Lookup table for getting band/channel from MHz
try:
	cursor.execute("DROP TABLE IF EXISTS `vtxReference`")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e

try:
	cursor.execute("""CREATE TABLE IF NOT EXISTS `vtxReference` (`vtxChan` VARCHAR(10))""")
	db.commit()
except MySQLdb.Error as e:
	print e
	db.rollback()
except MySQLdb.Warning as e:
	print e


db.close() # disconnect from server
