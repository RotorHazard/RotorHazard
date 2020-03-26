import paho.mqtt.client as mqtt_client
import time
import json

from mqtt_topics import mqtt_publish_topics, mqtt_subscribe_topics
from VRxCV1_emulator import MQTT_Client
from eventmanager import Evt

# ClearView API
# cd ~
# git clone https://github.com/ryaniftron/clearview_interface_public.git --depth 1
# cd ~/clearview_interface_public/src/clearview-py
# python2 -m pip install -e .
import clearview 

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

        self._cv = clearview.ClearView(return_formatted_commands=True)

        #TODO the subscribe topics subscribe it to a node number by default
        #Don't hack by making node number *

        #TODO: pass in "CV1 to the MQTT_CLIENT maybe. "
        # There will be multiple clients, one for each protocol"
        # Probably best to manually add the subscriptions and callbacks
        self._mqttc = MQTT_Client(client_id="VRxController",
                                 broker_ip=VRxServer,
                                 subscribe_topics = None)

        self._add_subscribe_callbacks()
        self._mqttc.loop_start()
        num_nodes = len(node_frequencies)

        
        self._nodes = [VRxNode(self._mqttc, n, node_frequencies[n], self._cv) for n in range(8)]
        self._node_broadcast = VRxBroadcastNode(self._mqttc, -1, None, self._cv)

        #TODO is this the right way. Store data twice? Maybe it should be a member var.
        # If the decorators worked...
        self._frequency = [node.node_frequency for node in self._nodes]
        self._lock_status = [node.node_lock_status for node in self._nodes]
        self._camera_type = [node.node_camera_type for node in self._nodes]

        # Events
        self.Events.on(Evt.STARTUP, 'VRx', self.do_startup, {}, 200)
        self.Events.on(Evt.RACESTART, 'VRx', self.do_racestart, {}, 200)
        self.rxdata = {}

    def do_startup(self,arg):
        print("vrxc: Doing startup")

        # Request status of all receivers (static and variable)
        self.request_static_status(all=True)
        self.request_variable_status(all=True)

        for n in range(8):
            print("LOCK STATUS ",n)
            self.get_node_lock_status(n)

        # Update the DB with receivers that exist and their status
        # (Because the pi was already running, they should all be connected to the broker)
        # Even if the server.py is restarted, the broker continues to run:) 

        # Set the receiver's frequencies based on band/channel
    
    def do_racestart(self, arg):
        self.set_message_direct(VRxALL,"GO!")

    
    ##############
    ## MQTT Status
    ##############
    def request_static_status(self, node_number=VRxALL, all=False):
        #self._mqttc.publish()
        #TODO 
        print("TODO request static status")
        #raise NotImplementedError

    def request_variable_status(self, node_number=VRxALL, all=False):
        #self._mqttc.publish()
        #TODO 
        print("TODO request variable status")
        #raise NotImplementedError

    


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
        node = self._nodes[node_number]
        report_req = node.get_node_lock_status()

        #return self._nodes[node_number].node_lock_status


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
    
    #############################
    # Private Functions for MQTT
    #############################

    def _add_subscribe_callbacks(self):
        for rx_type in mqtt_subscribe_topics:
            topics = mqtt_subscribe_topics[rx_type]

            # All response
            topic_tuple = topics["receiver_response_all"]
            self._add_subscribe_callback(topic_tuple, self.on_message_resp_all)
            
            # Node response
            print(topics)
            topic_tuple = topics["receiver_response_node"]
            self._add_subscribe_callback(topic_tuple, self.on_message_resp_node)

            # Connection
            topic_tuple  = topics["receiver_connection"]
            self._add_subscribe_callback(topic_tuple, self.on_message_connection)

            # Targetted Response
            topic_tuple = topics["receiver_response_targeted"]
            self._add_subscribe_callback(topic_tuple, self.on_message_resp_targeted)




    def _add_subscribe_callback(self, topic_tuple, callback):     
        formatter_name = topic_tuple[1]
        
        if formatter_name in ["#","+"]:   # subscibe to all at single level (+) or recursively all (#)
            topic = topic_tuple[0]%formatter_name
        elif formatter_name is None:
            topic = topic_tuple[0]
        elif isinstance(topic_tuple,tuple):
            raise ValueError("Uncaptured formatter_name: %s"%formatter_name)
        elif isinstance(topic_tuple,str):
            topic = topic_tuple
        else:
            raise TypeError("topic_tuple not of correct type: %s"%topic_tuple)
        
        self._mqttc.message_callback_add(topic, callback)
        self._mqttc.subscribe(topic)
            

    def on_message_connection(self, client, userdata, message):
        rx_name = message.topic
        connection_status = message.payload
        printc("Connection message received:", rx_name,"=>", connection_status)
        try:
            self.rxdata[rx_name]["connection"] = connection_status
        except KeyError:
            self.rxdata[rx_name] = {"connection": connection_status}

    def on_message_resp_all(self, client, userdata, message):
        payload = message.payload
        printc("TODO on_message_resp_all => %s"%(payload))

    def on_message_resp_node(self, client, userdata, message):
        topic = message.topic
        node_number = topic[-1]
        payload = message.payload
        printc("TODO on_message_resp_node for node %s => %s"%(node_number, payload))

    def on_message_resp_targeted(self, client, userdata, message):
        topic = message.topic
        rx_name = topic.split('/')[-1]
        payload = message.payload
        printc("TODO on_message_resp_targeted for receiver %s => %s"%(rx_name, payload))

CRED = '\033[91m'
CEND = '\033[0m'
def printc(*args):
    print(CRED + ' '.join(args) + CEND)

    

class VRxNode:
    """Commands and Requests apply to all receivers at a node number"""
    def __init__(self, 
                 mqtt_client,
                 node_number, 
                 node_frequency, 
                 cv,
                 node_camera_type = 'A',
                 ):
        self._mqttc = mqtt_client
        self._cv = cv

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
        messages = self._cv.set_custom_frequency(self._cv.bc_id, frequency)
        for m in messages:
            print(topic,m)
            self._mqttc.publish(topic,m)

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
        # topic = mqtt_publish_topics["cv1"]["receiver_request_node_active_topic"][0]%self.__node_number
        # self._mqttc.publish(topic,
        #                    "?")
        # time.sleep(0.1)
        # return self._node_lock_status
        pass
        print("TODO node_lock_status property")

    def get_node_lock_status(self,):
        topic = mqtt_publish_topics["cv1"]["receiver_request_node_all_topic"][0]%self.__node_number
        report_req = self._cv.get_lock_format(self.__node_number+1)
        self._mqttc.publish(topic,report_req[0])
        return report_req

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

    # Set node 3's frequency to 5781
    vrxc.set_node_frequency(3,5781)


if __name__ == "__main__":
    main()






 