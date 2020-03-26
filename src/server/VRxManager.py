'''
VRx management
'''

from eventmanager import Evt
from VRxController import VRxController

VRxALL = -1

class VRxManager:
	vrxc = None #holds VRxController object

	controllers = {}
	'''
	list of vcs
	[address] = {
		(status)
	}
	'''

	primary = []
	'''
	maps specific VRx to nodes (primary assignments)
	[address, address, None, ... ]
	'''

	def __init__(self, eventmanager, VRxServer):
		self.Events = eventmanager
		self.vrxc = VRxController(VRxServer,
                         [5740,
                          5760,
                          5780,
                          5800,
                          5820,
                          5840,
                          5860,
                          5880,])
		# self.primary = [None, None, None, None, None, None, None, None]
		# self.Events.on(Evt.RACESTART, 'VRx', self.displayStart, {}, 200)

	"""
	def connect(self, VRxObj):
		'''
		VRxObj = {
			address: (address),
			status: {
					"frequency": 5300..6000,
					"band": A/B/E/F/R/L/U/D,
					"channel": 1..8,
					"lock": t/f,
					...
				}
			}
		'''
		self.controllers[VRxObj.address] = {}
		self.controllers[VRxObj.address] = update(VRxObj.status)

	def disconnect(self, VRx):
		if VRx in self.controllers:
			del self.controllers[VRx]

	def pingAll(self):
		for VRx in self.controllers:
			result = VRxController.ping(VRx)
			if not result:
				disconnect(VRx)

	def getAllVRx(self):
		# get list of all connected VRx
		return self.controllers

	def getStatus(self, address):
		# get information from VRx (lock, etc.)
		status = VRxController.getStatus(address)
		self.controllers[address] = update(status)
		return status

	def assignPrimary(self, node_index, address):
		# assigns VRx to get status from
		self.primary[node_index] = address
	"""

	def setFrequency(self, node, frequency):
		self.vrxc.set_node_frequency(node, frequency)

	"""
	def sendPilotNames(self, names):
		# pilot names by node
		VRxController.setPilotNames(VRxProtocol.CV2, names)

	def displayMessage(self, node, message):
		output = (message[:40]) if len(data) > 40 else message
		VRxController.setMessage(VRxProtocol.CV2, node, output)

		output = (message[:8]) if len(data) > 8 else message
		VRxController.setMessage(VRxProtocol.BFOSD, node, output)

	def displayStaging(self):
		VRxController.setMessage(VRxProtocol.CV2, node, 'Ready')

	def displayStart(self):
		VRxController.setMessage(VRxProtocol.CV2, node, '>> Go <<')

	def displayResults(self, race):
		# race results
		# data = {ranks, total times, etc...}
		'''
		for node in race:
			VRxController.setMessage(VRxProtocol.CV2, node, ...)
		'''
		pass

	def displayStop(self):
		VRxController.setMessage(VRxProtocol.CV2, node, 'STOP')

	def displayCrossing(self, node, race):
		# get race times
		# data = {next split, last split, lap time...}
		output = '...'
		VRxController.setMessage(VRxProtocol.CV2, node, output)

	def setTimer(self, start, end):
		# current timer
		# data is pi time
		VRxController.setTimer(start, end)
	"""


class VRxProtocol:
	CV2 = 0
	BFOSD = 1
	TBS = 2
