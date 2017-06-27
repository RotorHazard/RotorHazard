class Node:
    def __init__(self):
        self.frequency = 0
        self.current_rssi = 0
        self.trigger_rssi = 0
        self.last_lap_id = -1

    def get_settings_json(self):
        return {'frequency': self.frequency, 'current_rssi': self.current_rssi, 'trigger_rssi': self.trigger_rssi}
