#
# Page Cache
#

class PageCache:
	def __init__(self):
		# deprecated properties (need removed)
		self.data = {}
		self.building = False
		self.valid = False

		self._data = {} # Cache of complete results page
		self._buildToken = False # Time of result generation or false if no results are being calculated
		self._valid = False # Whether cache is valid

	def get_cache(self):
		return self._data

	def get_buildToken(self):
		return self._buildToken

	def get_valid(self):
		return self._valid

	def set_cache(self, data):
		self._data = data

	def get_buildToken(self, buildToken):
		self._buildToken = buildToken

	def get_valid(self, valid):
		self._valid = valid
