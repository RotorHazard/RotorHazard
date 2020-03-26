import paho.mqtt.client as mqtt_client
import time
import json

from mqtt_topics import mqtt_publish_topics, mqtt_subscribe_topics



class VRxController:
    """Every video receiver has the following methods and data attributes"""
    def __init__(self, mqtt_hostname, node_frequencies):
        self.mqttc = mqtt_client.Client(client_id="VRxController", clean_session=True)
        self.mqttc.connect(mqtt_hostname)

        # Subscibe to all topics
        for rec_ver in mqtt_subscribe_topics:
            rec_topics = mqtt_subscribe_topics[rec_ver]
            for rec_topic in rec_topics:

                # Format with subtopics if they exist
                try:
                    rec_topic = rec_topic%'*'
                except TypeError:
                    pass
                
                self.mqttc.subscribe(rec_topic)

        if len(node_frequencies) != 8:
            raise ValueError("node_frequencies must be length 8")
        self._nodes = [VRxNode(self.mqttc, n, node_frequencies[n]) for n in range(8)]
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
        for node_number in frequencies:
            f = frequencies[node_number]
            self._nodes[node_number].node_frequency = f

    def set_node_frequency(self, node_number, frequency):
        node = self._nodes[node_number]
        node.set_node_frequency(frequency)

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
                 mqtt_client,
                 node_number, 
                 node_frequency, 
                 node_camera_type = 'A',
                 ):
        self.mqttc = mqtt_client

        self.MIN_NODE_NUM = 0
        self.MAX_NODE_NUM = 7

        if self.MIN_NODE_NUM <= node_number <= self.MAX_NODE_NUM:
            self.__node_number = node_number
        else:
            raise Exception("node_number out of range")

        self._node_frequency = node_frequency
        self._node_camera_type = node_camera_type
        self._node_lock_status = None

    @property
    def node_number(self):
        """Get the node number"""
        print("node property get")
        return self.__node_number

    @node_number.setter
    def node_number(self, node_number):
        if self.MIN_NODE_NUM <= node_number <= self.MAX_NODE_NUM:
            # TODO change the node number of all receivers and apply the settings of the other node number
            raise NotImplementedError
            print("x")
            # self._node_number = node_number
        else:
            raise Exception("node_number out of range")

    @property
    def node_frequency(self, ):
        """Gets the frequency of a node"""
        #print("getfrequency of", self.__node_number)
        return self._node_frequency

    @node_frequency.setter
    def node_frequency(self, frequency):
        """Sets all receivers at this node number to the new frequency"""
        print("setfrequency")
        raise NotImplementedError

    def set_node_frequency(self, frequency):
        """Sets all receivers at this node number to the new frequency"""
        topic = mqtt_publish_topics["cv1"]["receiver_command_node_topic"]%self.__node_number
        message = {"frequency":frequency}
        self.mqttc.publish(topic,
                           json.dumps(message))

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
        topic = mqtt_publish_topics["cv1"]["receiver_request_node_active_topic"]%self.__node_number
        self.mqttc.publish(topic,
                           "?")
        time.sleep(0.1)
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

    # Set node 3's frequency to 5781
    vrxc.set_node_frequency(3,5781)


if __name__ == "__main__":
    main()




 