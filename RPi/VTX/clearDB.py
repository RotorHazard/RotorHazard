#import smbus
##import time

import MySQLdb

# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )

# prepare a cursor object using cursor() method
cursor = db.cursor()

# Prepare SQL query to INSERT a record into the database.
sql = "TRUNCATE TABLE races"
try:
   # Execute the SQL command
   cursor.execute(sql)
   # Commit your changes in the database
   db.commit()
except:
   # Rollback in case there is any error
   db.rollback()

# disconnect from server
db.close()


##i2c = smbus.SMBus(1)
##addr = 8 # address of the arduino I2C
##
#### reset the lap to 0
##i2c.write_byte_data(addr, 0x0B, 0)
##time.sleep(0.5)
