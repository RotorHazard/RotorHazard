# VTX Timer by Scott Chin
# This version will poll the arduino with command 0x90
# It returns the data in an array with [lap,minutes, seconds, milliseconds]

import smbus
import time

import MySQLdb



# Open database connection
db = MySQLdb.connect("localhost","root","delta5fpv","vtx" )

# prepare a cursor object using cursor() method
cursor = db.cursor()


# read the startstop value for the loop
sql = "SELECT * FROM setup \
       WHERE ID = 1"
try:
   # Execute the SQL command
   cursor.execute(sql)
   # Fetch all the rows in a list of lists.
   results = cursor.fetchall()
   for row in results:
##      race = row[0]
      ss = row[1]
      # Now print fetched result
##      print "race=%d,sss=%d" % \
##             (race, ss )
      startstop=ss
   db.commit()
except:
   print "Error: unable to fecth data"


if startstop == 0:
   # update startstop flag to 1 to start polling
   sql = "UPDATE setup SET startstop = 1 \
          WHERE ID = 1"
   try:
      # Execute the SQL command
      cursor.execute(sql)
      # Commit your changes in the database
      db.commit()
   except:
      # Rollback in case there is any error
      db.rollback()
   startstop = 1
else:
   # update startstop flag to 0 to stop polling
   sql = "UPDATE setup SET startstop = 0 \
          WHERE ID = 1"
   try:
      # Execute the SQL command
      cursor.execute(sql)
      # Commit your changes in the database
      db.commit()
   except:
      # Rollback in case there is any error
      db.rollback()
   startstop=0




i2c = smbus.SMBus(1)
addr = 8 # address of node 1 I2C
addr2 = 10 # address of node 2 I2C
addr3 = 12 # address of node 3 I2C
addr4 = 14 # address of node 4 I2C
addr5 = 16 # address of node 5 I2C
addr6 = 18 # address of node 6 I2C

# Reset the lap counter on the arduino
i2c.write_byte_data(addr, 0x0B, 0)
time.sleep(0.25)
i2c.write_byte_data(addr2, 0x0B, 0)
time.sleep(0.25)
i2c.write_byte_data(addr3, 0x0B, 0)
time.sleep(0.25)
i2c.write_byte_data(addr4, 0x0B, 0)
time.sleep(0.5)
i2c.write_byte_data(addr5, 0x0B, 0)
time.sleep(0.5)
i2c.write_byte_data(addr6, 0x0B, 0)
time.sleep(0.5)

lapcounter=0
minutes=0
seconds=0
millisec=0

lapcounter2=0
minutes2=0
seconds2=0
millisec2=0

lapcounter3=0
minutes3=0
seconds3=0
millisec3=0

lapcounter4=0
minutes4=0
seconds4=0
millisec4=0

lapcounter5=0
minutes5=0
seconds5=0
millisec5=0

lapcounter6=0
minutes6=0
seconds6=0
millisec6=0


while startstop == 1:
    try:
        ## Node 1 Read the three bytes from minutes, seconds, and milliseconds
        lapdata = i2c.read_i2c_block_data(addr, 0x90, 4)
        if lapdata[0] != lapcounter:
            print "Lap %d %d:%d:%d" %(lapdata[0],lapdata[1],lapdata[2],lapdata[3])
            lapcounter = lapdata[0]
            minutes = lapdata[1]
            seconds = lapdata[2]
            millisec = lapdata[3]

            # Insert the lap data into the database
            sql = "INSERT INTO races(racegroup, \
                   race, pilot, lap, min, sec, millisec) \
                   VALUES ('%d', '%d', '%d', '%d', '%d', '%d', '%d' )" % \
                   (1, 1, 1, lapcounter, minutes, seconds, millisec)
            try:
               # Execute the SQL command
               cursor.execute(sql)
               # Commit your changes in the database
               db.commit()
            except:
               # Rollback in case there is any error
               db.rollback()
        time.sleep(0.25)

        ## Node 2 Read the three bytes from minutes, seconds, and milliseconds.
        lapdata2 = i2c.read_i2c_block_data(addr2, 0x90, 4)
        if lapdata2[0] != lapcounter2:
            print "Lap %d %d:%d:%d" %(lapdata2[0],lapdata2[1],lapdata2[2],lapdata2[3])
            lapcounter2 = lapdata2[0]
            minutes2 = lapdata2[1]
            seconds2 = lapdata2[2]
            millisec2 = lapdata2[3]

            # Insert the lap data into the database
            sql = "INSERT INTO races(racegroup, \
                   race, pilot, lap, min, sec, millisec) \
                   VALUES ('%d', '%d', '%d', '%d', '%d', '%d', '%d' )" % \
                   (1, 1, 2, lapcounter2, minutes2, seconds2, millisec2)
            try:
               # Execute the SQL command
               cursor.execute(sql)
               # Commit your changes in the database
               db.commit()
            except:
               # Rollback in case there is any error
               db.rollback()
        time.sleep(0.25)

        ## Node 3 Read the three bytes from minutes, seconds, and milliseconds.
        lapdata3 = i2c.read_i2c_block_data(addr3, 0x90, 4)
        if lapdata3[0] != lapcounter3:
            print "Lap %d %d:%d:%d" %(lapdata3[0],lapdata3[1],lapdata3[2],lapdata3[3])
            lapcounter3 = lapdata3[0]
            minutes3 = lapdata3[1]
            seconds3 = lapdata3[2]
            millisec3 = lapdata3[3]

            # Insert the lap data into the database
            sql = "INSERT INTO races(racegroup, \
                   race, pilot, lap, min, sec, millisec) \
                   VALUES ('%d', '%d', '%d', '%d', '%d', '%d', '%d' )" % \
                   (1, 1, 3, lapcounter3, minutes3, seconds3, millisec3)
            try:
               # Execute the SQL command
               cursor.execute(sql)
               # Commit your changes in the database
               db.commit()
            except:
               # Rollback in case there is any error
               db.rollback()
        time.sleep(0.25)

        ## Node 4 Read the three bytes from minutes, seconds, and milliseconds.
        lapdata4 = i2c.read_i2c_block_data(addr4, 0x90, 4)
        if lapdata4[0] != lapcounter4:
            print "Lap %d %d:%d:%d" %(lapdata4[0],lapdata4[1],lapdata4[2],lapdata4[3])
            lapcounter4 = lapdata4[0]
            minutes4 = lapdata4[1]
            seconds4 = lapdata4[2]
            millisec4 = lapdata4[3]

            # Insert the lap data into the database
            sql = "INSERT INTO races(racegroup, \
                   race, pilot, lap, min, sec, millisec) \
                   VALUES ('%d', '%d', '%d', '%d', '%d', '%d', '%d' )" % \
                   (1, 1, 4, lapcounter4, minutes4, seconds4, millisec4)
            try:
               # Execute the SQL command
               cursor.execute(sql)
               # Commit your changes in the database
               db.commit()
            except:
               # Rollback in case there is any error
               db.rollback()
        time.sleep(0.25)

        ## Node 5 Read the three bytes from minutes, seconds, and milliseconds.
        lapdata5 = i2c.read_i2c_block_data(addr5, 0x90, 4)
        if lapdata5[0] != lapcounter5:
            print "Lap %d %d:%d:%d" %(lapdata5[0],lapdata5[1],lapdata5[2],lapdata5[3])
            lapcounter5 = lapdata5[0]
            minutes5 = lapdata5[1]
            seconds5 = lapdata5[2]
            millisec5 = lapdata5[3]

            # Insert the lap data into the database
            sql = "INSERT INTO races(racegroup, \
                   race, pilot, lap, min, sec, millisec) \
                   VALUES ('%d', '%d', '%d', '%d', '%d', '%d', '%d' )" % \
                   (1, 1, 5, lapcounter5, minutes5, seconds5, millisec5)
            try:
               # Execute the SQL command
               cursor.execute(sql)
               # Commit your changes in the database
               db.commit()
            except:
               # Rollback in case there is any error
               db.rollback()
        time.sleep(0.25)

        ## Node 6 Read the three bytes from minutes, seconds, and milliseconds.
        lapdata6 = i2c.read_i2c_block_data(addr6, 0x90, 4)
        if lapdata6[0] != lapcounter6:
            print "Lap %d %d:%d:%d" %(lapdata6[0],lapdata6[1],lapdata6[2],lapdata6[3])
            lapcounter6 = lapdata6[0]
            minutes6 = lapdata6[1]
            seconds6 = lapdata6[2]
            millisec6 = lapdata6[3]

            # Insert the lap data into the database
            sql = "INSERT INTO races(racegroup, \
                   race, pilot, lap, min, sec, millisec) \
                   VALUES ('%d', '%d', '%d', '%d', '%d', '%d', '%d' )" % \
                   (1, 1, 6, lapcounter6, minutes6, seconds6, millisec6)
            try:
               # Execute the SQL command
               cursor.execute(sql)
               # Commit your changes in the database
               db.commit()
            except:
               # Rollback in case there is any error
               db.rollback()
        time.sleep(0.25)


        # Read the startstop value to see if it changed
        sql = "SELECT * FROM setup \
               WHERE ID = 1"
        try:
           # Execute the SQL command
           cursor.execute(sql)
           # Fetch all the rows in a list of lists.
           results = cursor.fetchall()
           for row in results:
##              race = row[0]
              ss = row[1]
              # Now print fetched result
##              print "race=%d,ss=%d" % \
##                     (race, ss )
              startstop = ss
##              print startstop

           db.commit()
        except:
           print "Error: unable to fecth data"

        
        time.sleep(0.5)
    except IOError as e:
        print e


# disconnect from server
db.close()
