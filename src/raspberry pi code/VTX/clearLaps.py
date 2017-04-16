# VTX Timer by Scott Chin
#
# Use after all the laps data has been recorded 
#
# Removes all laps from the database races table

import MySQLdb

# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )
cursor = db.cursor()

sql = "TRUNCATE TABLE races"
try:
	cursor.execute(sql) # Execute the SQL command
	db.commit() # Commit your changes in the database
except:
	db.rollback() # Rollback in case there is any error

db.close() # disconnect from server