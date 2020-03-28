import paho.mqtt.client as mqtt_client
import time
import json

from mqtt_topics import mqtt_publish_topics, mqtt_subscribe_topics
from VRxCV1_emulator import MQTT_Client

from eventmanager import Evt

VRxALL = -1

#TODO import clearview communcation protocol and use it here



class VRxController:
    """Every video receiver has the following methods and data attributes"""
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

    
    def __init__(self, eventmanager, VRxServer, node_frequencies):
        self.Events = eventmanager

        #TODO the subscribe topics subscribe it to a node number by default
        #Don't hack by making node number *

        # Probably best to manually add the subscriptions and callbacks
        self._mqttc = MQTT_Client(client_id="VRxController",
                                 broker_ip=VRxServer,
                                 subscribe_topics = mqtt_subscribe_topics)
        self._mqttc.loop_start()

        num_nodes = len(node_frequencies)

        
        self._nodes = [VRxNode(self._mqttc, n, node_frequencies[n]) for n in range(8)]

        #TODO is this the right way. Store data twice? Maybe it should be a member var.
        # If the decorators worked...
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

    ##############
    # OSD Messages
    ##############

    def set_message_direct(self, node_number, message):
        """set a message directly. Truncated if over length"""

    




class VRxNode:
    """Commands and Requests apply to all receivers at a node number"""
    def __init__(self, 
                 mqtt_client,
                 node_number, 
                 node_frequency, 
                 node_camera_type = 'A',
                 ):
        self._mqttc = mqtt_client

        self.MIN_NODE_NUM = 0
        self.MAX_NODE_NUM = 7

        if self.MIN_NODE_NUM <= node_number <= self.MAX_NODE_NUM:
            self.__node_number = node_number
        elif node_number == -1:
            print("todo this is the broadcast node. May have special methods")
        else:
            raise Exception("node_number out of range")

        self._node_frequency = node_frequency
        self._node_camera_type = node_camera_type
        self._node_lock_status = None


        """
        osd_fields are used to format the OSD string with multiple pieces of data

        example fields names:
        * cur_lap_count
        * pilot_name
        * lap_time
        * split_time
        * total_laps

        The osd fields have the actual data (_osd_field_data),
        and the order (_osd_field_order)
        """
        self._osd_field_data = {}
        self._osd_field_order = {}

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
        topic = mqtt_publish_topics["cv1"]["receiver_command_node_topic"][0]%self.__node_number
        message = {"frequency":frequency}
        self._mqttc.publish(topic,
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
        topic = mqtt_publish_topics["cv1"]["receiver_request_node_active_topic"][0]%self.__node_number
        self._mqttc.publish(topic,
                           "?")
        time.sleep(0.1)
        return self._node_lock_status

    def set_message(self, message):
        """Send a raw message to the OSD"""


    def set_osd_field(self, field_data):
        """sets an  osd field data object. Updates OSD.
        That field must also be shown on the OSD
        
        Input:
            field_data: dictionary 
                *keys = field names (str), value = field value (str)
        """

        for field in field_data:
            if field not in self._osd_field_data:
                self.set_field_order({field: -1})

            self._osd_field_data[field] = field_data[field]

    def set_field_order(self, field_order):
        """sets an  osd field data order. Updates OSD.
        That field must also be shown on the OSD
        
        Input:
            field_data: dictionary 
                *keys = field names (str), value = field order (int)
                A field order of -1 disables it. 
                Field orders must be unique
        """
        for field in field_order:
                self._osd_field_order[field] = field_order
        self._update_osd_by_fields()

    def _update_osd_by_fields(self):
        #todo
        # Get a list of keys sorted by field_order
        # concatenate the data togeter with a " " separator
        # send the OSD an update command

        #todo check against limit each addition and truncate based on field priority
        pass


class VRxBroadcastNode(VRxNode):
    pass
    #Todo broadcast node may look a bit different, but similar to VRxNode


class packet_formatter:
    def __init__(self):
        pass

    def format_command(self, command_name):
        if command_name == "frequency":
            command = {
                "cv1": self.get_cv1_base_format()
            }

    def get_cv1_base_format(self):
        clearview_specs = {
            'message_start_char': '\n',
            'message_end_char': '\r',
            'message_csum': '%',
            'mess_src': 9,
            'baud': 57600,
            'bc_id': 0
        }

        # base_format = (clearview_specs[message_start_char] + 
        #        '%i' + 
        #        str(clearview_specs[mess_src] + 
        #        '%s' + 
        #        clearview_specs[message_csum] + 
        #        clearview_specs[message_end_char])

        # return base_format




def main():
    # vrxc = VRxController("192.168.0.110",
    #                      [5740,
    #                       5760,
    #                       5780,
    #                       5800,
    #                       5820,
    #                       5840,
    #                       5860,
    #                       5880,])

    # # Set node 3's frequency to 5781
    # vrxc.set_node_frequency(3,5781)
    pass


if __name__ == "__main__":
    main()




 