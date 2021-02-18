import paho.mqtt.client as mqtt_client
import time
import json
import logging
import gevent
import traceback
from monotonic import monotonic

from mqtt_topics import mqtt_publish_topics, mqtt_subscribe_topics, ESP_COMMANDS
from VRxCV1_emulator import MQTT_Client
from eventmanager import Evt
from Language import __
import Results
from RHRace import WinCondition
import RHUtils
import Database
import Options

# Sample configuration:
#     "VRX_CONTROL": {
#         "HOST": "localhost",
#         "ENABLED": true
#     }
#
# HOST domain or IP address of MQTT server for VRx Control messages
# ENABLED:true is required.
# ONLY ONE server may use VRx Control on a given network at a time. Setting ENABLED to false
# is useful to store configuration settings when disabling a timer from VRx Control.

# ClearView API
# cd ~
# git clone https://github.com/ryaniftron/clearview_interface_public.git --depth 1
# cd ~/clearview_interface_public/src/clearview-py
# python2 -m pip install -e .
import clearview

VRxALL = -1
MINIMUM_PAYLOAD = 7

class VRxController:

    def __init__(self, eventmanager, vrx_config, race_obj, seat_frequencies):
        self.Events = eventmanager
        self.RACE = race_obj
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)
        self.logger.debug("TEST DEBUG")
        self.logger.info("TEST INFO")
        print(self.logger.getEffectiveLevel())
        # Stored receiver data
        self.rx_data = {}

        #ClearView API object
        # self._cv = clearview.ClearView(return_formatted_commands=True)

        self.config = self.validate_config(vrx_config)

        # TODO the subscribe topics subscribe it to a seat number by default
        # Don't hack by making seat number a wildcard

        # TODO: pass in "CV1 to the MQTT_CLIENT because
        # there can be multiple clients, one for each protocol.
        # The MQTT_CLIENT should not know about what it is supposed to be doing
        # The VRxController can then run multiple clients, but duplicate messaging will have to be avoided
        # This could be done in the publisher by only passing messages to the clients that need it

        self._mqttc = MQTT_Client(client_id="VRxController",
                                 broker_ip=self.config["HOST"],
                                 subscribe_topics = None)

        self._add_subscribe_callbacks()
        self._mqttc.loop_start()
        self.num_seats = len(seat_frequencies)

        self.seat_number_range = (0,7)
        self._seats = [VRxSeat(self._mqttc, n, seat_frequencies[n], seat_number_range=self.seat_number_range) for n in range(self.num_seats)]
        self._seat_broadcast = VRxBroadcastSeat(self._mqttc)

        # Events
        self.Events.on(Evt.STARTUP, 'VRx', self.do_startup)
        self.Events.on(Evt.HEAT_SET, 'VRx', self.do_heat_set)
        self.Events.on(Evt.RACE_STAGE, 'VRx', self.do_race_stage, {}, 75)
        self.Events.on(Evt.RACE_START, 'VRx', self.do_race_start, {}, 75)
        self.Events.on(Evt.RACE_FINISH, 'VRx', self.do_race_finish)
        self.Events.on(Evt.RACE_STOP, 'VRx', self.do_race_stop)
        self.Events.on(Evt.RACE_LAP_RECORDED, 'VRx', self.do_lap_recorded_json, {}, 200, True)
        self.Events.on(Evt.LAPS_CLEAR, 'VRx', self.do_laps_clear)
        self.Events.on(Evt.LAP_DELETE, 'VRx', self.do_lap_delete_json, {}, 200, True)
        self.Events.on(Evt.FREQUENCY_SET, 'VRx', self.do_frequency_set, {}, 200, True)
        self.Events.on(Evt.MESSAGE_INTERRUPT, 'VRx', self.do_send_message)

    def validate_config(self, supplied_config):
        """Ensure config values are within range and reasonable values"""

        default_config = {
            'HOST': 'localhost',
        }
        saved_config = default_config

        for k, v_default in default_config.items():
            if k not in supplied_config:
                self.logger.warning("VRX Config does not include config key '%s'. Using '%s'"%(k, v_default))
            else:
                saved_config[k] = supplied_config[k]

        return saved_config

    def do_startup(self,arg):
        self.logger.info("VRx Control Starting up")

        self._seat_broadcast.reset_lock()
        # Request status of all receivers (static and variable)
        self.request_static_status()
        self.request_variable_status()
        self._seat_broadcast.turn_off_osd()

        for i in range(self.num_seats):
            self.get_seat_lock_status(i)
            gevent.spawn(self.set_seat_frequency, i, self._seats[i]._seat_frequency)

        # Update the DB with receivers that exist and their status
        # (Because the pi was already running, they should all be connected to the broker)
        # Even if the server.py is restarted, the broker continues to run:)

    def do_heat_set(self, arg):
        self.logger.info("VRx Signaling Heat Set")
        try:
            heat_id = arg["heat_id"]
        except KeyError:
            self.logger.error("Unable to send callsigns. heat_id not found in event.")
            return

        for heatseat in Database.HeatNode.query.filter_by(heat_id=heat_id).all():
            heatseat_index = heatseat.seat_index
            if heatseat_index < self.num_seats:  # TODO this may break with non-contiguous nodes
                if heatseat.pilot_id != Database.PILOT_ID_NONE:
                    pilot = Database.Pilot.query.get(heatseat.pilot_id)
                    self.set_message_direct(heatseat_index, pilot.callsign)
                else:
                    self.set_message_direct(heatseat_index, __("-None-"))

    def do_race_stage(self, arg):
        self.logger.info("VRx Signaling Race Stage")
        self.set_message_direct(VRxALL, __("Ready"))

    def do_race_start(self, arg):
        self.logger.info("VRx Signaling Race Start")
        self.set_message_direct(VRxALL, __("Go"))

    def do_race_finish(self, arg):
        self.logger.info("VRx Signaling Race Finish")
        self.set_message_direct(VRxALL, __("Finish"))

    def do_race_stop(self, arg):
        self.logger.info("VRx Signaling Race Stop")
        self.set_message_direct(VRxALL, __("Race Stopped. Land Now."))

    def do_send_message(self, arg):
        self.set_message_direct(VRxALL, arg['message'])

    def do_laps_clear(self, arg):
        self.logger.info("VRx Signaling Laps Clear")
        self.set_message_direct(VRxALL, "---")

    def do_frequency_set(self, arg):
        self.logger.info("Setting frequency from event")
        try:
            seat_index = arg["nodeIndex"]
        except KeyError:
            self.logger.error("Unable to set frequency. nodeIndex not found in event")
            return
        try:
            frequency = arg["frequency"]
        except KeyError:
            self.logger.error("Unable to set frequency. frequency not found in event")
            return

        self.set_seat_frequency(seat_index, frequency)


    def do_lap_recorded_json(self, args):
        """
        Records a lap using the json interface for all the lap objects

        Note: The lap recorded event doesn't occur if the lap is below the min lap time, or there are no pilots, or no heats
        """

        try:
            VL = VRxLap(args)
        except ValueError as v:
            self.logger.error(v)
            return

        print(VL._seat_index)


        # fastest lap && 3 consecutive are the most different
    def do_lap_delete_json(self, args):
        """

        """
        self.logger.warning("Called untested do_lap_delete_json")
        self.do_lap_recorded_json(args)

    def do_lap_recorded(self, args):
        '''
        *** Deprecated ***
        '''
        raise DeprecationWarning("Use do_lap_recorded_json")
        print("LAP")

        RESULTS_TIMEOUT = 5 # maximum time to wait for results to generate
        LAP_HEADER = Options.get('osd_lapHeader')
        POS_HEADER = Options.get('osd_positionHeader')

        if 'node_index' in args:
            seat_index = args['node_index']
        else:
            self.logger.warning('Failed to send results: Seat not specified')
            return False

        if 'lap_info' in args:
            lap_info = args['lap_info']
        else:
            self.logger.warning('Failed to send results: Lap info not sent')
            return False

        results = self.RACE.results

        lap_info_json = json.dumps(lap_info)

        '''
        # send message to crosser
        seat_dest = seat_index
        self.send_lap_object(seat_dest, lap_info_json)

        # show split when next pilot crosses
        if lap_info['next_rank']['position'] != None:
            seat_dest = lap_info['next_rank']['seat']
            self.send_lap_object(seat_dest, lap_info_json)
        '''


        '''
        Format and send messages (Legacy)
        '''

        # Server options
        LAP_HEADER = Options.get('osd_lapHeader', 'L')
        POS_HEADER = Options.get('osd_positionHeader', '')
        BEST_LAP_TEXT = __('Best Lap')
        HOLSESHOT_TEXT = __('HS')

        # "Pos-Callsign L[n]|0:00:00"
        message = POS_HEADER + lap_info['current']['position'] + '-' + \
            lap_info['current']['callsign'][:10] + ' '

        if lap_info['current']['lap_number'] >= 1:
            message += LAP_HEADER

        message += str(lap_info['current']['lap_number']) + '|' + \
            RHUtils.time_format(lap_info['current']['last_lap_time'])

        if lap_info['race']['win_condition'] == WinCondition.FASTEST_3_CONSECUTIVE:
            # "Pos-Callsign L[n]|0:00:00 | #/0:00.000" (current | best consecutives)
            if lap_info['current']['lap_number'] >= 3:
                message += ' | 3/' + RHUtils.time_format(lap_info['current']['consecutives'])
            elif lap_info['current']['lap_number'] == 2:
                message += ' | 2/' + RHUtils.time_format(lap_info['current']['total_time_laps'])

        elif lap_info['race']['win_condition'] == WinCondition.FASTEST_LAP:
            if lap_info['next_rank']['position'] != None:
                # pilot in 2nd or lower
                # "Pos-Callsign L[n]|0:00:00 / +0:00.000 Callsign"
                message += ' / +' + RHUtils.time_format(lap_info['next_rank']['split_time']) + ' ' + lap_info['next_rank']['callsign'][:10]
            elif lap_info['is_best_lap']:
                # pilot in 1st and is best lap
                # "Pos:Callsign L[n]:0:00:00 / Best"
                message += ' / ' + BEST_LAP_TEXT
        else:
            # WinCondition.MOST_LAPS
            # WinCondition.FIRST_TO_LAP_X
            # WinCondition.NONE

            # "Pos-Callsign L[n]|0:00:00 / +0:00.000 Callsign"
            if lap_info['next_rank']:
                if lap_info['next_rank']['position'] != None:
                    message += ' / +' + RHUtils.time_format(lap_info['next_rank']['split_time']) + ' ' + lap_info['next_rank']['callsign'][:10]

        # send message to crosser
        seat_dest = seat_index
        self.set_message_direct(seat_dest, message)
        self.logger.debug('msg s{1}:  {0}'.format(message, seat_dest))

        # show split when next pilot crosses
        if lap_info['next_rank']:
            if lap_info['next_rank']['position'] != None:
                if lap_info['race']['win_condition'] == WinCondition.FASTEST_3_CONSECUTIVE or lap_info['race']['win_condition'] == WinCondition.FASTEST_LAP:
                    # don't update
                    pass

                else:
                    # WinCondition.MOST_LAPS
                    # WinCondition.FIRST_TO_LAP_X
                    # WinCondition.NONE

                    # update pilot ahead with split-behind

                    # "Pos-Callsign L[n]|0:00:00"
                    message = POS_HEADER + lap_info['next_rank']['position'] + '-' + lap_info['next_rank']['callsign'][:10] + ' '

                    if lap_info['next_rank']['lap_number'] >= 1:
                        message += LAP_HEADER

                    message += str(lap_info['next_rank']['lap_number']) + '|' + RHUtils.time_format(lap_info['next_rank']['last_lap_time'])

                    # "Pos-Callsign L[n]|0:00:00 / -0:00.000 Callsign"
                    message += ' / -' + RHUtils.time_format(lap_info['next_rank']['split_time']) + ' ' + lap_info['current']['callsign'][:10]

                    seat_dest = lap_info['next_rank']['seat']
                    self.set_message_direct(seat_dest, message)
                    self.logger.debug('msg s{1}:  {0}'.format(message, seat_dest))


    ##############
    ## MQTT Status
    ##############

    def request_static_status(self, seat_number=VRxALL):
        if seat_number == VRxALL:
            seat = self._seat_broadcast
            seat.request_static_status()
        else:
            self._seats[seat_number].request_static_status()

    def request_variable_status(self, seat_number=VRxALL):
        if seat_number == VRxALL:
            seat = self._seat_broadcast
            seat.request_variable_status()
        else:
            self._seats[seat_number].request_variable_status()

    ##############
    ## Seat Number
    ##############

    def set_seat_number(self, desired_seat_num=None, current_seat_num=None, serial_num=None ):
        """Sets the seat subscription number to desired_number

        If targetting all devices at a certain seat, use 'current_seat_num'
        If targetting a single receiver serial number, use 'serial_num'
        If targetting all receivers, don't supply either 'current_seat_num' or 'serial_num'
        """
        MIN_SEAT_NUM = self.seat_number_range[0]
        MAX_SEAT_NUM = self.seat_number_range[1]
        desired_seat_num = int(desired_seat_num)
        if not MIN_SEAT_NUM <= desired_seat_num <= MAX_SEAT_NUM:
            return ValueError("Desired Seat Number %s out of range in set_seat_number"%desired_seat_num)

        if current_seat_num is not None:
            current_seat_num = int(current_seat_num)
            if not MIN_SEAT_NUM <= current_seat_num <= MAX_SEAT_NUM:
                return ValueError("Desired Seat Number %s out of range in set_seat_number"%current_seat_num)
            self._seats[current_seat_num].set_seat_number(desired_seat_num)
            return

        if serial_num is not None:
            topic = mqtt_publish_topics["cv1"]["receiver_command_esp_targeted_topic"][0]%serial_num
            cmd = json.dumps({"seat": str(desired_seat_num)})
            self._mqttc.publish(topic, cmd)
            self.rx_data[serial_num]["needs_config"] = True
            return

        raise NotImplementedError("TODO Broadcast set all seat number")

    ###########
    # Frequency
    ###########

    def set_seat_frequency(self, seat_number, frequency):
        fmsg = __("Frequency Change: ") + str(frequency)
        seat = self._seats[seat_number]
        seat.set_seat_frequency(frequency)

    def set_target_frequency(self, target, frequency):
        if frequency != RHUtils.FREQUENCY_ID_NONE:
            topic = mqtt_publish_topics["cv1"]["receiver_command_esp_targeted_topic"][0]%target

            # For ClearView, set the band and channel
            cv_bc = clearview.comspecs.frequency_to_bandchannel_dict(frequency)
            if cv_bc:
                self._mqttc.publish(topic, json.dumps(cv_bc))
            else:
                self.logger.warning("Unable to set ClearView frequency to %s", frequency)

            self.logger.debug("Set frequency for %s to %d", target, frequency)

    def get_seat_frequency(self, seat_number, frequency):
        self._seats[seat_number].seat_frequency

    #############
    # Lock Status
    #############

    # @property
    # def lock_status(self):
    #     self._lock_status = [seat.seat_lock_status for seat in self._seats]
    #     return self._lock_status

    def get_seat_lock_status(self, seat_number=VRxALL):
        if seat_number == VRxALL:
            seat = self._seat_broadcast
            seat.get_seat_lock_status()
        else:
            seat = self._seats[seat_number]
            seat.get_seat_lock_status()

        #return self._seats[seat_number].seat_lock_status

    #############
    # Camera Type
    #############

    @property
    def camera_type(self):
        self._camera_type = [seat.seat_camera_type for seat in self._seats]
        return self._camera_type

    @camera_type.setter
    def camera_type(self, camera_types):
        """ set the receiver camera types
        camera_types: dict
            key: seat_number
            value: desired camera_type in ['N','P','A']
        """
        for seat_index in camera_types:
            c = camera_types[seat_index]
            self._seats[seat_index].seat_camera_type = c

    def set_seat_camera_type(self, seat_number, camera_type):
        self._seats[seat_number].seat_camera_type = camera_type

    def get_seat_camera_type(self, seat_number, camera_type):
        self._seats[seat_number].seat_camera_type

    ##############
    # OSD Messages
    ##############

    def set_message_direct(self, seat_number, message):
        """set a message directly. Truncated if over length"""
        if message==None:
            self.logger.error("No message")
            return

        if seat_number == VRxALL:
            seat = self._seat_broadcast
            seat.set_message_direct(message)
        else:
            self._seats[seat_number].set_message_direct(message)

    #############################
    # Private Functions for MQTT
    #############################

    def _add_subscribe_callbacks(self):
        for rx_type in mqtt_subscribe_topics:
            topics = mqtt_subscribe_topics[rx_type]

            # All response
            topic_tuple = topics["receiver_response_all"]
            self._add_subscribe_callback(topic_tuple, self.on_message_resp_all)

            # Seat response
            topic_tuple = topics["receiver_response_seat"]
            self._add_subscribe_callback(topic_tuple, self.on_message_resp_seat)


            # Connection
            topic_tuple  = topics["receiver_connection"]
            self._add_subscribe_callback(topic_tuple, self.on_message_connection)

            # Targeted Response
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

    def perform_initial_receiver_config(self, target):
        """ Given the unique identifier of a receiver, perform the initial config"""
        initial_config_success = False

        try:
            sn = self.rx_data[target]["seat"]
        except KeyError:
            self.logger.info("No seat number available for %s yet", target)
        else:
            self.logger.info("Performing initial configuration for %s", target)

            seat_number = int(self.rx_data[target]['seat'])
            seat = self._seats[seat_number]
            frequency = seat.seat_frequency
            self.set_target_frequency(target, frequency)
            self.turn_off_osd_targeted(target)

            # TODO: send most relevant OSD information

            self.rx_data[target]["needs_config"] = False
            initial_config_success = True

        return initial_config_success




    def on_message_connection(self, client, userdata, message):
        rx_name = message.topic.split('/')[1]

        if rx_name == 'VRxController':
            return

        connection_status = message.payload
        self.logger.info("Found MQTT device: %s => %s" % (rx_name,connection_status))
        rx_data = self.rx_data.setdefault(rx_name,{"connection": connection_status})

        if int(connection_status) == 1:
            self.logger.info("Device %s is not yet configured by the server after a successful connection. Conducting some config now" % rx_name)
            rx_data["needs_config"] = True

            # Start by requesting the status of the device that just joined.
            # At this point, it could be any MQTT device becaue we haven't filtered by receivers.
            # See TODO in on_message_status
            self.req_status_targeted("variable", rx_name)
            self.req_status_targeted("static", rx_name)




        #TODO only fire event if the data changed
        self.Events.trigger(Evt.VRX_DATA_RECEIVE, {
            'rx_name': rx_name,
            })

    def on_message_resp_all(self, client, userdata, message):
        payload = message.payload
        self.logger.info("TODO on_message_resp_all => %s"%(payload.strip()))

    def on_message_resp_seat(self, client, userdata, message):
        topic = message.topic
        seat_number = topic[-1]
        payload = message.payload
        self.logger.info("TODO on_message_resp_seat for seat %s => %s"%(seat_number, payload.strip()))

    def on_message_resp_targeted(self, client, userdata, message):
        topic = message.topic
        rx_name = topic.split('/')[-1]
        payload = message.payload
        if len(payload) >= MINIMUM_PAYLOAD:
            rx_data = self.rx_data.setdefault(rx_name,{"connection": "1"}) #TODO this is probably not needed
            try:
                extracted_data = json.loads(payload)

            except:
                self.logger.warning("Can't load json data from '%s' of '%s'", rx_name, payload)
                self.logger.debug(traceback.format_exc())
                rx_data["valid_rx"] = False
            else:
                rx_data["valid_rx"] = True
                rx_data.update(extracted_data)

                if "lock" in extracted_data:
                    rep_lock = extracted_data["lock"]

                    rx_data["chosen_camera_type"] = rep_lock[0]
                    rx_data["cam_forced_or_auto"] = rep_lock[1]
                    rx_data["lock_status"] = rep_lock[2]



                #TODO only fire event if the data changed
                self.Events.trigger(Evt.VRX_DATA_RECEIVE, {
                    'rx_name': rx_name,
                    })


                if rx_data["needs_config"] == True and rx_data["valid_rx"] == True:
                    self.perform_initial_receiver_config(rx_name)


    def req_status_targeted(self, mode = "variable",serial_num = None):
        """Ask a targeted receiver for its status.
        Inputs:
            *mode: ["variable","static"]
            *serial_num: The devices's unique serial number to target it
        """

        if mode not in ["variable", "static"]:
            self.logger.error("Incorrect mode in req_status_targeted")
            return None
        if serial_num not in self.rx_data.keys():
            self.logger.error("RX %s does not exist", serial_num)
            return None

        topic = mqtt_publish_topics["cv1"]["receiver_command_esp_targeted_topic"][0]%serial_num
        if mode == "variable":
            cmd = ESP_COMMANDS["Request Variable Status"]
        elif mode == "static":
            cmd = ESP_COMMANDS["Request Static Status"]
        else:
            raise Exception("Error checking mode has failed")
        self._mqttc.publish(topic,cmd)


    def turn_off_osd_targeted(self, target):
        """Turns off all OSD elements except user message"""
        topic = mqtt_publish_topics["cv1"]["receiver_command_esp_targeted_topic"][0]%target
        cmd = json.dumps({"osd_visibility" : "D"})
        self._mqttc.publish(topic, cmd)
        return cmd

    def turn_on_osd_targeted(self, target):
        """Turns on all OSD elements except user message"""
        topic = mqtt_publish_topics["cv1"]["receiver_command_esp_targeted_topic"][0]%target
        cmd = json.dumps({"osd_visibility" : "E"})
        self._mqttc.publish(topic, cmd)
        return cmd


CRED = '\033[91m'
CEND = '\033[0m'
def printc(*args):
    print(CRED + ' '.join(args) + CEND)

class BaseVRxSeat:
    """Seat controller for both the broadcast and individual seats"""
    def __init__(self,
                 mqtt_client
                 ):

        self._mqttc = mqtt_client
        self.logger = logging.getLogger(self.__class__.__name__)

class VRxSeat(BaseVRxSeat):
    """Commands and Requests apply to all receivers at a seat number"""
    def __init__(self,
                 mqtt_client,
                 seat_number,
                 seat_frequency,
                 seat_number_range = (0,7), #(min,max)
                 seat_camera_type = 'A'
                 ):
        BaseVRxSeat.__init__(self, mqtt_client)

        # RH refers to seats 0 to 7
        self.MIN_SEAT_NUM = seat_number_range[0]
        self.MAX_SEAT_NUM = seat_number_range[1]

        if self.MIN_SEAT_NUM <= seat_number <= self.MAX_SEAT_NUM:
            self._seat_number = seat_number
        elif seat_number == VRxALL:
            raise Exception("Use the broadcast seat")
        else:
            raise Exception("seat_number %d out of range", seat_number)

        self._seat_frequency = seat_frequency
        self._seat_camera_type = seat_camera_type
        self._seat_lock_status = None

        """
        osd_fields are used to format the OSD string with multiple pieces of data
        Follows this protocol:
        https://github.com/RotorHazard/RotorHazard/wiki/Specification:-Realtime-lap-information
        """
        self._osd_field_data = {}

        # TODO specify the return value for commands.
        #   Do we return the command sent or some sort of result from mqtt?

    @property
    def seat_number(self):
        """Get the seat number"""
        self.logger.debug("seat property get")
        return self._seat_number

    @seat_number.setter
    def seat_number(self, seat_number):
        if self.MIN_SEAT_NUM <= seat_number <= self.MAX_SEAT_NUM:
            # TODO change the seat number of all receivers and apply the settings of the other seat number
            raise NotImplementedError
            # self._seat_number = seat_number
        else:
            raise Exception("seat_number out of range")

    def set_seat_number(self, new_seat_number):
        topic = mqtt_publish_topics["cv1"]["receiver_command_esp_seat_topic"][0]%self._seat_number
        cmd = cmd = json.dumps({"seat": str(new_seat_number)})
        self._mqttc.publish(topic,cmd)
        return

    @property
    def seat_frequency(self, ):
        """Gets the frequency of a seat"""
        return self._seat_frequency

    @seat_frequency.setter
    def seat_frequency(self, frequency):
        """Sets all receivers at this seat number to the new frequency"""
        raise NotImplementedError

    def set_seat_frequency(self, frequency):
        FREQUENCY_TIMEOUT = 10

        time_now = monotonic()
        time_expires = time_now + FREQUENCY_TIMEOUT
        self.set_message_direct(__("!!! Frequency changing to {0} in <10s !!!").format(frequency))
        gevent.sleep(10)

        self.set_seat_frequency_direct(frequency)
        self.set_message_direct(__(""))

    def set_seat_frequency_direct(self, frequency):
        """Sets all receivers at this seat number to the new frequency"""
        self._seat_frequency = frequency
        if frequency != RHUtils.FREQUENCY_ID_NONE:

            # For ClearView, set the band and channel
            cv_bc = clearview.comspecs.frequency_to_bandchannel_dict(frequency)
            if cv_bc:
                topic = mqtt_publish_topics["cv1"]["receiver_command_esp_seat_topic"][0]%self._seat_number
                self._mqttc.publish(topic, json.dumps(cv_bc))

            else:
                self.logger.warning("Unable to set ClearView frequency to %s", frequency)

    @property
    def seat_camera_type(self, ):
        """Get the configured camera type for a seat number"""
        return self._seat_camera_type

    @seat_camera_type.setter
    def seat_camera_type(self, camera_type):
        if camera_type.capitalize in ["A","N","P"]:
            raise NotImplementedError
        else:
            raise Exception("camera_type out of range")

    @property
    def seat_lock_status(self, ):
        # topic = mqtt_publish_topics["cv1"]["receiver_request_seat_active_topic"][0]%self._seat_number
        # self._mqttc.publish(topic,
        #                    "?")
        # time.sleep(0.1)
        # return self._seat_lock_status
        pass
        print("TODO seat_lock_status property")

    def get_seat_lock_status(self,):
        topic = mqtt_publish_topics["cv1"]["receiver_command_esp_seat_topic"][0]%self._seat_number
        report_req = json.dumps({"lock": "?"})
        self._mqttc.publish(topic,report_req)
        return report_req

    def request_static_status(self):
        topic = mqtt_publish_topics["cv1"]["receiver_command_esp_seat_topic"][0]%self._seat_number
        msg = ESP_COMMANDS["Request Static Status"]
        self._mqttc.publish(topic,msg)

    def request_variable_status(self):
        topic = mqtt_publish_topics["cv1"]["receiver_command_esp_seat_topic"][0]%self._seat_number
        msg = ESP_COMMANDS["Request Variable Status"]
        self._mqttc.publish(topic,msg)

    def set_message_direct(self, message):
        """Send a raw message to the OSD"""
        topic = mqtt_publish_topics["cv1"]["receiver_command_esp_seat_topic"][0]%self._seat_number
        cmd = json.dumps({"user_msg" : message})
        self._mqttc.publish(topic, cmd)
        return cmd

    def turn_off_osd(self):
        """Turns off all OSD elements except user message"""
        topic = mqtt_publish_topics["cv1"]["receiver_command_esp_seat_topic"][0]%self._seat_number
        cmd = json.dumps({"osd_visibility" : "D"})
        self._mqttc.publish(topic, cmd)
        return cmd

    def turn_on_osd(self):
        """Turns on all OSD elements except user message"""
        topic = mqtt_publish_topics["cv1"]["receiver_command_esp_seat_topic"][0]%self._seat_number
        cmd = json.dumps({"osd_visibility" : "E"})
        self._mqttc.publish(topic, cmd)
        return cmd

    def update_osd_on_lap(self):
        """Sends a combined OSD data packet"""
        topic = mqtt_publish_topics["cv1"]["receiver_command_esp_seat_topic"][0]%self._seat_number
        osd_data = {}

        # TODO append OSD data here

        cmd = json.dumps(osd_data)
        self._mqttc.publish(topic, cmd)
        return cmd


class VRxBroadcastSeat(BaseVRxSeat):
    def __init__(self,
                 mqtt_client
                 ):
        BaseVRxSeat.__init__(self, mqtt_client)
        self._cv_broadcast_id = clearview.comspecs.clearview_specs['bc_id']
        self._broadcast_cmd_topic = mqtt_publish_topics["cv1"]["receiver_command_all"][0]
        self._rx_cmd_esp_all_topic = mqtt_publish_topics["cv1"]["receiver_command_esp_all_topic"][0]

    def set_message_direct(self, message):
        """Send a raw message to all OSD's"""
        topic = self._rx_cmd_esp_all_topic
        cmd = json.dumps({"user_msg" : message})
        self._mqttc.publish(topic, cmd)
        return cmd

    def turn_off_osd(self):
        """Turns off all OSD elements except user message"""
        topic = self._rx_cmd_esp_all_topic
        cmd = json.dumps({"osd_visibility" : "D"})
        self._mqttc.publish(topic, cmd)
        return cmd

    def turn_on_osd(self):
        """Turns on all OSD elements except user message"""
        topic = self._rx_cmd_esp_all_topic
        cmd = json.dumps({"osd_visibility" : "E"})
        self._mqttc.publish(topic, cmd)
        return cmd

    def reset_lock(self):
        """ Resets lock of all receivers"""
        topic = self._rx_cmd_esp_all_topic
        cmd = json.dumps({"lock": "1"})
        self._mqttc.publish(topic, cmd)
        return cmd

    def request_static_status(self):
        topic = self._rx_cmd_esp_all_topic
        cmd = ESP_COMMANDS["Request Static Status"]
        self._mqttc.publish(topic,cmd)

    def request_variable_status(self):
        topic = self._rx_cmd_esp_all_topic
        cmd = ESP_COMMANDS["Request Variable Status"]
        self._mqttc.publish(topic,cmd)

    def get_seat_lock_status(self,):
        topic = mqtt_publish_topics["cv1"]["receiver_command_esp_all_topic"][0]
        report_req = json.dumps({"lock":"?"})
        self._mqttc.publish(topic,report_req)
        return report_req

class VRxLap:
    s_seat_index = "node_index"
    s_lap_info = "lap_info"
    s_racelap_info = "race"
    s_wincondition = "win_condition"

    s_current = "current"
    # current lap data strings
    class s_Current:
        """https://github.com/RotorHazard/RotorHazard/wiki/Specification:-Realtime-lap-information#current-current-lap-data-object"""
        position = "position"
        lap_number = "lap_number"
        last_lap_time = "last_lap_time"
        total_time = "total_time"
        total_time_laps = "total_time_laps"
        consecutives = "consecutives"
        is_best_lap = "is_best_lap"

    class Current:
        "Holds current lap data"
        pass

    def __init__(self, args):

        try:
            self._seat_index = args[self.s_seat_index]
        except KeyError:
            raise KeyError("%s not found in args"%(self.s_seat_index))

        try:
            wc = args[self.s_lap_info][self.s_racelap_info][self.s_wincondition]
            self._win_condition = wc
        except KeyError:
            raise KeyError("[%s][%s][%s] not found in args"%(
                            self.s_lap_info,
                            self.s_racelap_info,
                            self.s_wincondition
                            ))

        # Lap info is in the data, and current should always be
        lap_info = args[self.s_lap_info]
        cur = lap_info[self.s_current]

        self.parse_cur(cur)

        # TODO we don't get Options.osd_lapHeader or osd_positionHeader because the receiver already has them
        # However, if that updates in the UI, there needs to be an event for it
        # vrx_options or something
        # really, its a config just like camera, and is dependent on the pilot

        # We can ignore callsign
        position = cur[""]

    def parse_cur(self, cur):
        c = self.Current
        c.position = int(cur[self.s_Current.position])
        c.lap_number = int(cur[self.s_Current.lap_number])
        c.last_lap_time = int(cur[self.s_Current.last_lap_time])
        c.total_time = int(cur[self.s_Current.total_time])



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

    # # Set seat 3's frequency to 5781
    # vrxc.set_seat_frequency(3,5781)
    pass


if __name__ == "__main__":
    main()
