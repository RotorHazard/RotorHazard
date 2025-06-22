from Plugins import Plugins

class Sensors(Plugins):
    def __init__(self):
        Plugins.__init__(self, suffix='sensor')
        self.sensors_dict = {}
        self.environmental_data_update_tracker = 0

    def update_environmental_data(self):
        '''Updates environmental data.'''
        self.environmental_data_update_tracker += 1

        partition = (self.environmental_data_update_tracker % 2)
        for index, sensor in enumerate(self.data):
            if (index % 2) == partition:
                sensor.update()

    def discover(self, *args, **kwargs):
        Plugins.discover(self, *args, **kwargs)
        if not hasattr(self, 'data'):  # 'data' attribute should be setup by 'UserList' implementation
            self.data = []             # but just in case
        for sensor in self.data:
            self.sensors_dict[sensor.name] = sensor
