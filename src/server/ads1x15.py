# This library

import time
import smbus
import Adafruit_ADS1x15 #Install from here: https://github.com/adafruit/Adafruit_Python_ADS1x15

# For wiring, see https://learn.adafruit.com/raspberry-pi-analog-to-digital-converters/ads1015-slash-ads1115
# 			  and https://cdn-learn.adafruit.com/downloads/pdf/adafruit-4-channel-adc-breakouts.pdf


# Resistor Divider Factor(s) Note: For a typical lipo sensing divider, R1 is the larger resistance.  http://www.ohmslawcalculator.com/voltage-divider-calculator 
# See below for the circuit diagram
#
#    VBAT ------R1
#               |  
#               |--ADS pin
#				|				
#	 GND  ------R2
#


# The ADS1x15 has adjustable gain. The maximum voltages at each gain are shown below.
# The voltage at the ADS pin should not exceed the programmed gain limit below. Exceeding VDD will break the unit. 

GAIN_FACTORS = {
	2/3 : 6.144, #note, 2/3 gets cast to 0, so sending 0 in for this gain factor also works
	1 : 4.096,
	2 : 2.048,
	4 : 1.024,
	8 : 0.512,
	16 : 0.256,
}


VALID_HARDWARE_NAMES = {
	"ADS1115", 		#for the 16 bit 4-channel version
	"ADS1015",		#for the 12 bit 4-channel version
}

VALID_I2C_ADDRESSES = { 
	0x49, # ADR -> GND
	0x48, # ADR -> VDD , default if ADR pin is not connected
	0x4A, # ADR -> SDA
	0x4B, # ADR -> SCL
}

VALID_CONNECTED_CHANNELS = {
	0,
    1,
 	2,
 	3,	
}

# The code below is for scanning the i2c bus for ADS1X15 sensors
bus = smbus.SMBus(1) # 1 indicates /dev/i2c-1




class ADS1X15():
	def __init__(self,
		hardware_name = "ADS1115",		# Either ADS1115 or ADS1015
		connected_channels = [0,], 		# Which connected channels to use, pick any from 0,1,2,3
		gains = [1,], 					# ADC gains to use
		R1_Values = [22,], 				# R1 values for a voltage divider
		R2_Values =  [3.3,],			# R2 values for a voltage divider
		address = 0x48 , 			  	# The hex address, defaulting to 0x48 beccause that's what the address is when nothing is connected to ADR pin.
		correction_factors = [1.00,], 	# Correction factor for resistor tolerances. This value is limited from 0.9 to 1.1. If the displayed voltage is less than a multimeter says, increase the correction factor.
		debug_print = False,
	):
		self.debug_print = debug_print
		
		# Check hardware name is valid
		if hardware_name in VALID_HARDWARE_NAMES:
			self.hardware_name = hardware_name
		else:
			print ("Error: Invalid ADS hardware name.")
			self.exit_action()
		

		
		#Check connected_channels is within inclusive range of 0-3. Don't allow adding the same channel more than once
		self.connected_channels = []
		try: 		#try iterating on connected_channels
			for channel in connected_channels:
				if channel in self.connected_channels:
					print("Channel" ,channel, "is already added. Can't add it again.")
					self.exit_action()
				elif channel not in VALID_CONNECTED_CHANNELS:
					print("Error: Channel" ,channel, "is not possible to read from.")
					self.exit_action()
				else:
					self.connected_channels.append(channel)
		except TypeError: 		# maybe a single int was passed as connected_channels
			if connected_channels in VALID_CONNECTED_CHANNELS:
				print("Warning. connected_channels is not iterable. Use a list of one element if possible for full error checking.")
				self.connected_channels.append(connected_channels)
				
			

		
		self.gains = []
		try:
			for gain in gains:
				if gain in GAIN_FACTORS:
					self.gains.append(gain)
				else:
					print("Error: The gain of ",gain,"is not a valid gain. Valid gains include",GAIN_FACTORS.keys())
			else: 		#after appending all gains, check there is the right number of gains
				if len(gains) != len(self.connected_channels):
					print("Error: Number of configured gains is not equal to the number of connected_channels.")
					self.exit_action()
		except TypeError:		# maybe a single int was passed as connected_channels
			print("Warning. gains is not iterable. Use a list of one element if possible for full error checking.")
			if gains in GAIN_FACTORS:
					self.gains.append(gains)
			else:
				print("That gain also isn't a valid gain. Quitting")
				self.exit_action()
			
			
				
		try:
			if len(R1_Values) == len(R2_Values):
				#save the number of connected channels
				self.n_channels = len(R1_Values) 
			else: 
				print ("Error: The number of R1_Values and R2_Values is not the same.")
				self.exit_action()
		except TypeError:
			print("Warning. R1_Values or R2_Values is not iterable. Use a list of one element if possible for full error checking.")
			self.n_channels = 1
			
			
			
		if len(self.connected_channels) != self.n_channels:
			#add resistor ratios of 1 for the remainder.
			print ("Error: The number of resistor combinations is not equal to the number of configured channels")
			self.exit_action()
		
		#Set up resistor ratios
		self.resistor_ratios = []
		try:
			for i , (R1,R2) in enumerate(zip(R1_Values,R2_Values)):
				resistor_ratio = float(R2) / float(R1+ R2)
				self.resistor_ratios.append(resistor_ratio)
				if resistor_ratio > 0.50:
					print("Warning: Resistor ratio #",i,"Where R1 = ",R1," and R2 = ",R2, "is greater than 0.5. Make sure R1 and R2 are the correct order.")
		except TypeError:
			print("Warning. resistor_ratios is not iterable. Use a list of one element if possible for full error checking.")
			self.resistor_ratios.append(float(R2_Values) / float(R1_Values+ R2_Values))
			
		
		
		if address in VALID_I2C_ADDRESSES:
			self.address = address
		else:
			print ("Error: The ADC hex address is not valid.")
			self.exit_action()
			
		#Create the ADS1x15 object	
		if hardware_name == "ADS1115":
			self._adc = Adafruit_ADS1x15.ADS1115(address = self.address) 
			self.max_adc_value = 32767
		elif self.hardware_name == "ADS1015":
			self._adc = Adafruit_ADS1x15.ADS1015(address = self.address)
			self.max_adc_value = 2047
			
		# See if the device is connected during init.
		try:
			bus.read_byte(self.address)
			if self.debug_print:
				print("An i2c device has been detected by ads1x15. ")
			self.found_device = True
		except:
			if self.debug_print:
				print("Error: No i2c device detected on 0x{0:X}".format(self.address))	
				print("		Testing if any of the other possible ads1x15 addresses have devices...")
			self.found_device = False
			for test_address in VALID_I2C_ADDRESSES:
				if test_address != self.address: #only try the remaining addresses
					try:
						bus.read_byte(test_address)
						if self.debug_print:
							print("		*0x{0:X}: Device Found!".format(test_address))
					except:
						if self.debug_print:
							print("		*0x{0:X}: No Device Found.".format(test_address))
			#self.exit_action()
		
		#Correction factor for resistor tolerance fixing
		self.correction_factors = []
		try:
			if len(correction_factors) != self.n_channels:
				print("Error: The Number of correction factors is not equal to the number of configured channels") 	
				self.exit_action()
			else:
				for correction in correction_factors:
					if 0.90 <= correction <= 1.1:
						self.correction_factors.append(correction)
					else:
						print("Correction factor of ",correction,"is not between 0.9 and 1.1")
						print("For larger adjustment, tweak the resistor parameters")
						self.exit_action()
		except TypeError:
			print("Warning. correction_factors is not iterable. Use a list of one element if possible for full error checking.")
			self.correction_factors.append(correction_factors)
	
	#returns a dictionary where the key is the adc port number and value is the adc reading. If a reading fails, returns false for value.
	def get_adc_values(self):
		adc_dict = {}
		
		for index,channel_num in enumerate(self.connected_channels):
			try:
				adc_val = self._adc.read_adc(channel_num, gain=self.gains[index])
				adc_dict[channel_num] = adc_val
				
			except:
				adc_val = False
				adc_dict[channel_num] = adc_val
				print("Error: Unable to read ADC i2c address 0x{0:X} at pin {1} with gain {2}".format(self.address,channel_num,self.gains[index]))	
		return adc_dict
	
	#returns a dictionary where the key is the adc port number and value is the adc voltage. If a reading fails, returns false for value.
	def get_adc_voltages(self):
		adc_voltages = {}
		
		adc_values = self.get_adc_values()
		for index,channel_num in enumerate(adc_values):
			
			#Leave bad readings as false
			if adc_values[channel_num] == False:
				adc_voltages[channel_num] = adc_values[channel_num]
			else:
				adc_voltages[channel_num] = float(adc_values[channel_num]) / self.max_adc_value * GAIN_FACTORS[self.gains[index]]
		return adc_voltages
	
	#returns a dictionary where the key is the adc port number and value is the input voltage (battery). If a reading fails, returns false for value.	
	def get_input_voltages(self):
		input_voltages = {}
		
		adc_voltages = self.get_adc_voltages()
		for index,channel_num in enumerate(adc_voltages): #use enumerate because adc_voltages is a dictionary with channel number keys while resistor_ratios is just a list
			
			#Leave bad readings as false
			if adc_voltages[channel_num] == False:
				input_voltages[channel_num] = adc_voltages[channel_num]
			else:
				#Apply the resistor ratio and correction factor here to get input voltage
				input_voltages[channel_num] = adc_voltages[channel_num] / self.resistor_ratios[index] * self.correction_factors[index] 
		
		return input_voltages
		
	def exit_action(self):
		print ("Calling quit() from ADS_Voltage_Sensor due to an error.")
		quit()
		
			
		
			
			
#Here's an example usage. 
if __name__ == "__main__":
	#ads_default = ADS1X15() #can use the default settings
	
	ads_custom = ADS1X15( # Here's an example with all the settings configured. 
		hardware_name = "ADS1115",		
		connected_channels = [0,], 	
		gains = [1,], 				
		R1_Values = [22,], 			
		R2_Values =  [3.3,],		
		address = 0x49,					
		correction_factors = [1.01045,]
	)
	
	#take a voltage reading
	voltage_readings = ads_custom.get_input_voltages()
	
	#print the port and voltage
	print("Channel | Voltage")
	for channel_num in voltage_readings:
		print("{0:7d} | {1:6.3f}".format(channel_num,voltage_readings[channel_num]))
	

	
		


