#
# Page Cache
#

class PageCache:
	def __init__(self):
		self.data = {} # Cache of complete results page
		self.building = False # Whether results are being calculated
		self.valid = False # Whether cache is valid (False = regenerate cache)
