# VTX Timer by Scott Chin
# This file will increase the trigger threshold on the arduino with command 0x82
# It returns the data in an array with [rssiTrig]

import smbus
import time

import MySQLdb

# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )

# prepare a cursor object using cursor() method
cursor = db.cursor()


i2c = smbus.SMBus(1)
addr = 8 # address of the arduino I2C

try:
    ## Read the one byte for rssiTrigger.
    trigger = i2c.read_i2c_block_data(addr, 0x82, 1)

    rssitrig1 = trigger[0]
    # Insert the trigger data into the database
    sql = "UPDATE setup SET trig1 = '%d' \
	   WHERE ID = 1" %\
	   (rssitrig1)
    try:
       # Execute the SQL command
       cursor.execute(sql)
       # Commit your changes in the database
       db.commit()
    except:
       # Rollback in case there is any error
       db.rollback()

    time.sleep(0.5)
except IOError as e:
    print e


# disconnect from server
db.close()
