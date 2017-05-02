#
# Starts the main comms loop with the nodes, reads rssi and lap info from nodes, writes lap info to DB on new lap

import smbus
import time

# Start i2c bus
i2c = smbus.SMBus(1)

print " "
try:
	i2cBlockData = i2c.read_i2c_block_data(8, 0x90, 5) # Request: rssi, lap, min, sec, ms
	time.sleep(0.01)
	print "i2c address: 8"
	print i2cBlockData
except IOError as e:
	print e
	
