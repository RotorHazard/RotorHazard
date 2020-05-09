import paho.mqtt.client as mqtt_client
import time
import json
import logging
from monotonic import monotonic

from mqtt_topics import mqtt_publish_topics, mqtt_subscribe_topics, ESP_COMMANDS
from VRxCV1_emulator import MQTT_Client
from eventmanager import Evt
from Language import __
import Results
from RHRace import WinCondition
import RHUtils

# ClearView API
# cd ~
# git clone https://github.com/ryaniftron/clearview_interface_public.git --depth 1
# cd ~/clearview_interface_public/src/clearview-py
# python2 -m pip install -e .
import clearview

VRxALL = -1

# logger = logging.getLogger(__name__)

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
        self.logger = logging.getLogger(self.__class__.__name__)
        self._cv = clearview.ClearView(return_formatted_commands=True)

        # TODO the subscribe topics subscribe it to a node number by default
        # Don't hack by making node number a wildcard

        # TODO: pass in "CV1 to the MQTT_CLIENT because
        # there can be multiple clients, one for each protocol.
        # The MQTT_CLIENT should not know about what it is supposed to be doing
        # The VRxController can then run multiple clients, but duplicate messaging will have to be avoided
        # This could be done in the publisher by only passing messages to the clients that need it


        self._mqttc = MQTT_Client(client_id="VRxController",
                                 broker_ip=VRxServer,
                                 subscribe_topics = None)

        self._add_subscribe_callbacks()
        self._mqttc.loop_start()
        num_nodes = len(node_frequencies)


        self._nodes = [VRxNode(self._mqttc,self._cv, n, node_frequencies[n]) for n in range(8)]
        self._node_broadcast = VRxBroadcastNode(self._mqttc, self._cv)

        #TODO is this the right way. Store data twice? Maybe it should be a member var.
        # If the decorators worked...
        self._frequency = [node.node_frequency for node in self._nodes]
        self._lock_status = [node.node_lock_status for node in self._nodes]
        self._camera_type = [node.node_camera_type for node in self._nodes]

        # Events
        self.Events.on(Evt.STARTUP, 'VRx', self.do_startup, {}, 200)
        self.Events.on(Evt.RACE_START, 'VRx', self.do_race_start, {}, 200)
        self.Events.on(Evt.RACE_FINISH, 'VRx', self.do_race_finish, {}, 200)
        self.Events.on(Evt.FREQUENCY_SET, 'VRx', self.do_frequency_set, {}, 50)
        self.Events.on(Evt.SEND_MESSAGE, 'VRx', self.do_send_message, {}, 200)
        self.Events.on(Evt.RACE_LAP_RECORDED, 'VRx', self.do_lap_recorded, {}, 200)

        # Stored receiver data
        self.rxdata = {}

    def do_startup(self,arg):
        self.logger.info("VRxC Starting up")

        # Request status of all receivers (static and variable)
        self.request_static_status()
        self.request_variable_status()
        self._node_broadcast.turn_off_osd()

        # Update the DB with receivers that exist and their status
        # (Because the pi was already running, they should all be connected to the broker)
        # Even if the server.py is restarted, the broker continues to run:)

        # Set the receiver's frequencies based on band/channel


    def do_race_start(self, arg):
        self.logger.info("VRx Signaling Race Start")
        self.set_message_direct(VRxALL, "GO")

    def do_race_finish(self, arg):
        self.logger.info("VRx Signaling Race Finish")
        self.set_message_direct(VRxALL, "FINISH")

    def do_send_message(self, arg):
        self.set_message_direct(VRxALL, arg['message'])

    def do_frequency_set(self, arg):
        self.logger.info("Setting frequency from event")
        try:
            node_index = arg["nodeIndex"]
        except KeyError:
            self.logger.error("Unable to set frequency. nodeIndex not found in event")
            return
        try:
            frequency = arg["frequency"]
        except KeyError:
            self.logger.error("unable to set frequency. frequency not found in event")
            return

        self.set_node_frequency(node_index, frequency)

    def do_lap_recorded(self, args):
        '''
        *** TODO: Formatting for hardware (OSD length, etc.)
        '''

        RESULTS_TIMEOUT = 5 # maximum time to wait for results to generate

        if 'race' in args:
            RACE = args['race']
        else:
            self.logger.warn('Failed to send results: Race not specified')
            return False

        if 'node_index' in args:
            node_index = args['node_index']
        else:
            self.logger.warn('Failed to send results: Node not specified')
            return False

        # wait for results to generate
        timeout = monotonic() + RESULTS_TIMEOUT
        while RACE.cacheStatus != Results.CacheStatus.VALID and time_now < timeout:
            time_now = monotonic()
            gevent.sleep()

        if RACE.cacheStatus == Results.CacheStatus.VALID:
            results = RACE.results

            # select correct results
            # *** leaderboard = results[results['meta']['primary_leaderboard']]
            win_condition = RACE.format.win_condition

            if win_condition == WinCondition.FASTEST_3_CONSECUTIVE:
                leaderboard = results['by_consecutives']
            elif win_condition == WinCondition.FASTEST_LAP:
                leaderboard = results['by_fastest_lap']
            else:
                # WinCondition.MOST_LAPS
                # WinCondition.FIRST_TO_LAP_X
                leaderboard = results['by_race_time']

            # get this node's results
            for index, result in enumerate(leaderboard):
                if result['node'] == node_index:
                    current_result = result
                    result_index = index
                    break

            # send the crossing node's result to this node's VRx
            current_lap = None
            if result['last_lap']:
                current_lap = result['last_lap']

                '''
                Re-implement after message queue exists

                message = str(result['position']) + ': ' + result['last_lap']
                node_dest = node_index
                self.set_message_direct(node_dest, message)
                self.logger.debug('msg node {1} | {0}'.format(message, node_dest))
                '''

            # get the next faster results
            next_rank_split = None
            next_rank_split_result = None
            if result['position'] > 1:
                next_rank_split_result = leaderboard[result['position']-2]

                if next_rank_split_result['total_time_raw']:
                    if win_condition == WinCondition.FASTEST_3_CONSECUTIVE:
                        next_rank_split = result['consecutives_raw'] - next_rank_split_result['consecutives_raw']
                    elif win_condition == WinCondition.FASTEST_LAP:
                        next_rank_split = result['last_lap_raw'] - next_rank_split_result['fastest_lap_raw']
                    else:
                        # WinCondition.MOST_LAPS
                        # WinCondition.FIRST_TO_LAP_X
                        next_rank_split = result['total_time_raw'] - next_rank_split_result['total_time_raw']

                    # send next faster result to this node's VRx
                    '''
                    Re-implement after message queue exists
                    message = __('Next') + ' (' + str(split_result['position']) + '): -' + RHUtils.time_format(split) + ' ' + split_result['callsign']
                    node_dest = node_index
                    self.set_message_direct(node_dest, message)
                    self.logger.debug('msg node {1} | {0}'.format(message, node_dest))
                    '''

                    '''
                    Re-implement after message queue exists
                    # send this result to next faster VRx
                    message = str(node_index) + ': +' + RHUtils.time_format(split) + ' ' + result['callsign']
                    node_dest = leaderboard[result['position']-2]['node']
                    self.set_message_direct(node_dest, message)
                    self.logger.debug('msg node {1} | {0}'.format(message, node_dest))
                    '''

            # get the fastest result
            first_rank_split = None
            first_rank_split_result = None
            if result['position'] > 2:
                first_rank_split_result = leaderboard[0]

                if next_rank_split_result['total_time_raw']:
                    if win_condition == WinCondition.FASTEST_3_CONSECUTIVE:
                        first_rank_split = result['consecutives'] - first_rank_split_result['consecutives']
                    elif win_condition == WinCondition.FASTEST_LAP:
                        first_rank_split = result['last_lap_raw'] - first_rank_split_result['fastest_lap']
                    else:
                        # WinCondition.MOST_LAPS
                        # WinCondition.FIRST_TO_LAP_X
                        first_rank_split = result['total_time_raw'] - first_rank_split_result['total_time_raw']

                    '''
                    Re-implement after message queue exists
                    # send the fastest result to this node's VRx
                    message = __('First') + ': -' + RHUtils.time_format(split) + ' ' + split_result['callsign']
                    node_dest = node_index
                    self.set_message_direct(node_dest, message)
                    self.logger.debug('msg node {1} | {0}'.format(message, node_dest))
                    '''

            # *** temporary: one-line lap readout ***
            # "Pilot1 L2 t:18.64  s-0.68"

            if result['laps']:
                message = result['callsign'][:12] + ':' + str(result['position']) + ' | L' + str(result['laps']) + ': ' + result['last_lap']
            else:
                message = result['callsign'][:12] + ':' + str(result['position']) + ' | HS: ' + result['total_time']

            if next_rank_split:
                message += ' / +' + RHUtils.time_format(next_rank_split) + ' (' + next_rank_split_result['callsign'][:12] + ')'

            node_dest = node_index
            self.set_message_direct(node_dest, message)
            self.logger.debug('msg node {1} | {0}'.format(message, node_dest))

        else:
            self.logger.warn('Failed to send results: Results not available')
            return False


    ##############
    ## MQTT Status
    ##############
    def request_static_status(self, node_number=VRxALL):
        if node_number == VRxALL:
            for node in self._nodes:
                node.request_static_status()
        else:
            self._nodes[node_number].request_static_status()

    def request_variable_status(self, node_number=VRxALL):
        if node_number == VRxALL:
            for node in self._nodes:
                node.request_variable_status()
        else:
            self._nodes[node_number].request_variable_status()



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
        if node_number == VRxALL:
            node = self._node_broadcast
            node.set_message(message)


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
        rx_name = message.topic.split('/')[1]
        connection_status = message.payload
        self.logger.info("Connection message received: %s => %s" % (rx_name,connection_status))
        try:
            self.rxdata[rx_name]["connection"] = connection_status
        except KeyError:
            self.rxdata[rx_name] = {"connection": connection_status}

        if int(connection_status) == 1:
            self.logger.warning("Receiver %s is not yet configured by the server after a successful connection" % rx_name)

            # TODO Do we set the receiver's settings now? What if they are flying?
            # We don't want to waste time if they just plugged in the ESP32 though


    def on_message_resp_all(self, client, userdata, message):
        payload = message.payload
        self.logger.debug("TODO on_message_resp_all => %s"%(payload))

    def on_message_resp_node(self, client, userdata, message):
        topic = message.topic
        node_number = topic[-1]
        payload = message.payload
        self.logger.debug("TODO on_message_resp_node for node %s => %s"%(node_number, payload))

    def on_message_resp_targeted(self, client, userdata, message):
        topic = message.topic
        rx_name = topic.split('/')[-1]
        payload = message.payload
        self.logger.debug("TODO on_message_resp_targeted for receiver %s => %s"%(rx_name, payload))

CRED = '\033[91m'
CEND = '\033[0m'
def printc(*args):
    print(CRED + ' '.join(args) + CEND)

class BaseVRxNode:
    """Node controller for both the broadcast and individual nodes"""
    def __init__(self,
                 mqtt_client,
                 cv,
                 ):

        self._mqttc = mqtt_client
        self._cv = cv
        self.logger = logging.getLogger(self.__class__.__name__)


class VRxNode(BaseVRxNode):
    """Commands and Requests apply to all receivers at a node number"""
    def __init__(self,
                 mqtt_client,
                 cv,
                 node_number,
                 node_frequency,
                 node_camera_type = 'A'
                 ):
        BaseVRxNode.__init__(self, mqtt_client, cv)

        # RH refers to nodes 0 to 7
        self.MIN_NODE_NUM = 0
        self.MAX_NODE_NUM = 7

        if self.MIN_NODE_NUM <= node_number <= self.MAX_NODE_NUM:
            self._node_number = node_number
        elif node_number == VRxALL:
            raise Exception("Use the broadcast node")
        else:
            raise Exception("node_number %d out of range", node_number)

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

        # TODO specify the return value for commands.
        #   Do we return the command sent or some sort of result from mqtt?

    @property
    def node_number(self):
        """Get the node number"""
        self.logger.debug("node property get")
        return self._node_number

    @node_number.setter
    def node_number(self, node_number):
        if self.MIN_NODE_NUM <= node_number <= self.MAX_NODE_NUM:
            # TODO change the node number of all receivers and apply the settings of the other node number
            raise NotImplementedError
            # self._node_number = node_number
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

    def set_node_frequency(self, frequency):
        """Sets all receivers at this node number to the new frequency"""
        topic = mqtt_publish_topics["cv1"]["receiver_command_node_topic"][0]%self._node_number
        messages = self._cv.set_custom_frequency(self._cv.bc_id, frequency)

        # set_custom_frequency returns multiple commands (one for channel and one for band)
        for m in messages:
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
        # topic = mqtt_publish_topics["cv1"]["receiver_request_node_active_topic"][0]%self._node_number
        # self._mqttc.publish(topic,
        #                    "?")
        # time.sleep(0.1)
        # return self._node_lock_status
        pass
        print("TODO node_lock_status property")

    def get_node_lock_status(self,):
        topic = mqtt_publish_topics["cv1"]["receiver_request_node_all_topic"][0]%self._node_number
        report_req = self._cv.get_lock_format(self._node_number+1)
        self._mqttc.publish(topic,report_req[0])
        return report_req

    def request_static_status(self):
        topic = mqtt_publish_topics["cv1"]["receiver_command_esp_node_topic"][0]%self._node_number
        msg = ESP_COMMANDS["Request Static Status"]
        self._mqttc.publish(topic,msg)

    def request_variable_status(self):
        topic = mqtt_publish_topics["cv1"]["receiver_command_esp_node_topic"][0]%self._node_number
        msg = ESP_COMMANDS["Request Variable Status"]
        self._mqttc.publish(topic,msg)

    def set_message(self, message):
        """Send a raw message to the OSD"""
        topic = mqtt_publish_topics["cv1"]["receiver_command_node_topic"][0]%self._node_number
        cmd = self._cv.set_user_message(self._node_number+1, message)
        self._mqttc.publish(topic, cmd)
        return cmd

    def _update_osd_by_fields(self):
        #todo
        # Get a list of keys sorted by field_order
        # concatenate the data togeter with a " " separator
        # send the OSD an update command

        #todo check against limit each addition and truncate based on field priority
        pass


class VRxBroadcastNode(BaseVRxNode):
    def __init__(self,
                 mqtt_client,
                 cv
                 ):
        BaseVRxNode.__init__(self, mqtt_client, cv)
        self._cv_broadcast_id = clearview.comspecs.clearview_specs['bc_id']
        self._broadcast_cmd_topic = mqtt_publish_topics["cv1"]["receiver_command_all"][0]

    def set_message(self, message):
        """Send a raw message to all OSD's"""
        topic = self._broadcast_cmd_topic
        cmd = self._cv.set_user_message(self._cv_broadcast_id, message)
        self._mqttc.publish(topic, cmd)
        return cmd

    def turn_off_osd(self):
        """Turns off all OSD elements except user message"""
        topic = self._broadcast_cmd_topic
        cmd = self._cv.hide_osd(self._cv_broadcast_id)
        self._mqttc.publish(topic, cmd)
        return cmd


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
