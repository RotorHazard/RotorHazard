import paho.mqtt.client as mqttc

from mqtt_topics import mqtt_publish_topics, mqtt_subscribe_topics


class VRxController:
    """Every video receiver has the following methods and data attributes"""
    def __init__(self, mqtt_hostname, node_frequencies):
        self.mqttc = mqttc(client_id="VRxController", clean_session=True)
        self.mqttc.connect(mqtt_hostname)

        if len(node_frequencies) != 8:
            raise ValueError("node_frequencies must be length 8")
        self._nodes = [VRxNode(mqtt_hostname, n, node_frequencies[n]) for n in range(8)]
        self._frequency = [node.node_frequency for node in self._nodes]
        self._lock_status = [node.node_lock_status for node in self._nodes]
        self._camera_type = [node.node_camera_type for node in self._nodes]

    ###########
    # Frequency
    ###########
    @property
    def frequency(self):
        return [node.node_frequency for node in self._nodes]

    @frequency.setter
    def frequency(self, frequencies):
        """ set the receiver frequencies
        frequencies: dict
            key: node_number
            value: desired frequency
        """
        for node_index in frequencies:
            f = frequencies[node_index]
            self._nodes[node_index].node_frequency = f

    def set_node_frequency(self, node_number, frequency):
        self._nodes[node_number].node_frequency = frequency

    def get_node_frequency(self, node_number, frequency):
        self._nodes[node_number].node_frequency

    #############
    # Lock Status
    #############

    @property
    def lock_status(self):
        self._lock_status = [node.node_lock_status for node in self._nodes]  
        return self._lock_status

    def get_node_lock_status(self, node_number):
        return self._nodes[node_number].node_lock_status


    #############
    # Camera Type
    #############

    @property
    def camera_type(self):
        self._camera_type = [node.node_camera_type for node in self._nodes]
        return self._camera_type

    @camera_type.setter
    def camera_type(self, camera_types):
        """ set the receiver camera types
        camera_types: dict
            key: node_number
            value: desired camera_type in ['N','P','A']
        """
        for node_index in camera_types:
            c = camera_types[node_index]
            self._nodes[node_index].node_camera_type = c

    def set_node_camera_type(self, node_number, camera_type):
        self._nodes[node_number].node_camera_type = camera_type

    def get_node_camera_type(self, node_number, camera_type):
        self._nodes[node_number].node_camera_type




class VRxNode:
    """Commands and Requests apply to all receivers at a node number"""
    def __init__(self, 
                 mqtt_hostname,
                 node_number, 
                 node_frequency, 
                 node_camera_type = 'A',
                 ):

        self.MIN_NODE_NUM = 0
        self.MAX_NODE_NUM = 7

        if self.MIN_NODE_NUM <= node_number <= self.MAX_NODE_NUM:
            self._node_number = node_number
        else:
            raise Exception("node_number out of range")

        self._node_frequency = node_frequency
        self._node_camera_type = node_camera_type
        self._node_lock_status = None

    @property
    def node_number(self):
        """Get the node number"""
        return self._node_number

    @node_number.setter
    def node_number(self, node_number):
        if self.MIN_NODE_NUM <= node_number <= self.MAX_NODE_NUM:
            # TODO change the node number of all receivers and apply the settings of the other node number
            raise NotImplementedError
            self._node_number = node_number
        else:
            raise Exception("node_number out of range")

    @property
    def node_frequency(self, ):
        """Gets the frequency of a node"""
        return self._node_frequency

    @node_frequency.setter
    def node_frequency(self, frequency):
        """Sets all receivers at this node number to the new frequency"""
        raise NotImplementedError

    @property
    def node_camera_type(self, ):
        """Get the configured camera type for a node number"""
        return self._node_camera_type

    @node_camera_type.setter
    def node_camera_type(self, camera_type):
        if camera_type.capitalize in ["A","N","P"]:
            raise NotImplementedError
        else:
            raise Exception("camera_type out of range")

    @property
    def node_lock_status(self, ):
        raise NotImplementedError
        return self._node_lock_status



def main():
    vrxc = VRxController("192.168.0.110",
                         [5740,
                          5760,
                          5780,
                          5800,
                          5820,
                          5840,
                          5860,
                          5880,])


if __name__ == "__main__":
    main()




 