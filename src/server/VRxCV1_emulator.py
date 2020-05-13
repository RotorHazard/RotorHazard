#VRxCV1_emulator.py

import paho.mqtt.client as mqtt_client
import socket
import argparse
import sys
import logging

import json

# mqtt topics are flipped for the VRX
from mqtt_topics import mqtt_publish_topics as mqtt_sub_topics
from mqtt_topics import mqtt_subscribe_topics as mqtt_pub_topics

from paho.mqtt.client import topic_matches_sub
from paho.mqtt.client import CONNACK_ACCEPTED
from paho.mqtt.client import CONNACK_REFUSED_PROTOCOL_VERSION
from paho.mqtt.client import CONNACK_REFUSED_IDENTIFIER_REJECTED
from paho.mqtt.client import CONNACK_REFUSED_SERVER_UNAVAILABLE
from paho.mqtt.client import CONNACK_REFUSED_BAD_USERNAME_PASSWORD
from paho.mqtt.client import CONNACK_REFUSED_NOT_AUTHORIZED



import time


class MQTT_Client:
    """General Purpose MQTT Client"""
    def __init__(self, client_id, broker_ip, subscribe_topics=None, node_number=0,debug=False):
        self._client_id = client_id
        self._broker_ip = broker_ip
        self._subscribe_topics_dict_at_start = subscribe_topics
        self._subscribed_topics = {}
        self._debug = debug
        #TODO I don't think the node number should be in here.
        # subscribed topics should be supplied preformatted using a helper written here

        self.logger = logging.getLogger(self.__class__.__name__)

        if 0 <= node_number <= 7:
            self._node_number = node_number
        else:
            raise ValueError("Node number out of range")

        # Start MQTT Client
        self._client = mqtt_client.Client(client_id=client_id, clean_session=True)
        
        self._set_will()
        self._bind_log_callback()

        self._bind_message_callbacks()
        
        self.initialize_mqtt() 

        

    # call this once
    def initialize_mqtt(self):
        self._client.on_connect = self.on_connect
        self._client.on_disconnect = self.on_disconnect
        # self._client.on_subscribe = self.on_subscribe

        self._connected_mqtt = False
        while not self._connected_mqtt:
            try:
                self._client.connect(self._broker_ip)
                self._subscribe_start()

            except socket.gaierror as e:
                self.logger.error("No device at '{0}'".format(self._broker_ip))
                raise e
            except socket.error as e:
                retry_time = 5
                self.logger.error("MQTT broker not alive at '{0}'. Waiting {1} seconds...".format(self._broker_ip, retry_time))  
                time.sleep(retry_time)                
            else:
                self._connected_mqtt = True

        self.loop_start = self._client.loop_start
        self.loop_forever = self._client.loop_forever
        self.message_callback_add = self._client.message_callback_add
        self.message_callback_remove = self._client.message_callback_remove
        self.subscribe = self._client.subscribe

     

    def on_message(self,client, userdata, message):
        self.logger.warning("Warning: Uncaptured message topic received: \n\t*Topic '%s'\n\t*Message:'%s'"%(message.topic,message.payload.strip()))
        self.logger.warning("\tIf this happens, make sure to bind the message to a function if subscribed to it.")

        # client.topic_matches_sub("cv/+","cv/a")
        if topic_matches_sub(self._subscribed_topics["receiver_response_targeted"] , message.topic):
            self.logger.info("on_message TODO sloppy fallback. Captured direct response from ", message.topic.split('/')[-1])
            #try parsing


    def on_subscribe(self,client, userdata, mid, granted_qos):
        raise NotImplementedError



    def on_log(self, mqttc, obj, level, string):
        if self.debug == True:
            self.logger.debug("%s %s %s"%(obj,level,string))

    def _set_will(self):
        self._last_will = {
            "topic": mqtt_pub_topics["cv1"]["receiver_connection"][0]%self._client_id,
            "payload": -1   # -1 on connection will indicate ungraceful disconnect
            # This could be from a power cycle, or some other bad error
        }

        self._client.will_set(self._last_will["topic"],
                                  self._last_will["payload"],
                                  1,    #QOS 1 guaranteed
                                  retain=False)
    
    def _bind_message_callbacks(self):
        self._client.on_message = self.on_message


    def _bind_log_callback(self):
        self._client.on_log = self.on_log

    def _subscribe_start(self):
        """ Subscribe to a bunch of topics in self._subscribe_topics_dict_at_start
        substituting in the node number and receiver serial number as needed
        """
        if self._subscribe_topics_dict_at_start is not None:
            subscribe_topics = self._subscribe_topics_dict_at_start
             # Subscibe to all topics
            for rec_ver in subscribe_topics:
                rec_topics = subscribe_topics[rec_ver]
                for topic_key in rec_topics:
                    rec_topic = rec_topics[topic_key]
                    # Format with subtopics if they exist
                    
                    formatter_name = rec_topic[1]
                    
                    if formatter_name == "node_number":
                        rec_topic = rec_topic[0]%self._node_number
                    elif formatter_name == "receiver_serial_num":
                        rec_topic = rec_topic[0]%self._client_id
                    elif formatter_name in ["#","+"]:   # subscibe to all at single level (+) or recursively all (#)
                        rec_topic = rec_topic[0]%formatter_name
                    elif formatter_name is None:
                        rec_topic = rec_topic[0]
                    elif isinstance(rec_topic,tuple):
                        raise ValueError("Uncaptured formatter_name: %s"%formatter_name)
                    elif isinstance(rec_topic,str):
                        pass
                    else:
                        raise TypeError("rec_topic not of correct type: %s"%rec_topic)
                    
                    self._client.subscribe(rec_topic)
                    # TODO use a factory method to add callbacks dynamically
                    # https://www.freecodecamp.org/news/dynamic-class-definition-in-python-3e6f7d20a381/
                    # self.message_callback_add() because we already bound that locally to this class
                    #
                    # For now, use on_message by comparing a list of topics and performing actions
                    # or see _add_message_callbacks in VRxCV_emulator
                    self.logger.info("Subscribing to %s"% rec_topic)
                    self._subscribed_topics[topic_key] = rec_topic


        

    def on_connect(self, client, userdata, flags, rc, properties=None):
        if rc != 0:
            raise("Connection error '%s' to broker"%self._get_rc_reason(rc))
        else:
            self.logger.info("Connected to mqtt broker with flags"+str(flags)+": result code "\
                   +self._get_rc_reason(rc))
          
        topic = self._last_will["topic"]
        payload = 1
        self.publish(topic,payload)

        

    def on_disconnect(self, client, userdata, rc):
        rc_name = self._get_rc_reason(rc)

        self.logger.warning("Disconnected from broker under result code %s"%rc_name)
        self._connected_mqtt = False

    def publish(self, topic, payload=None, qos=1, retain=False, properties=None):
        self._client.publish( topic, payload, qos, retain, properties)

    def disconnect_gracefully(self):
        self.logger.info("Gracefully disconnecting from broker")
        topic = self._last_will["topic"]
        payload = 0 #graceful disconnect

        self.publish(topic,payload)
        self._client.disconnect()
        self._client.loop_stop()

    def _get_rc_reason(self, rc_code):
        rc_dict = {
            CONNACK_ACCEPTED: "CONNACK_ACCEPTED",
            CONNACK_REFUSED_PROTOCOL_VERSION:"CONNACK_REFUSED_PROTOCOL_VERSION",
            CONNACK_REFUSED_IDENTIFIER_REJECTED:"CONNACK_REFUSED_IDENTIFIER_REJECTED",
            CONNACK_REFUSED_SERVER_UNAVAILABLE:"CONNACK_REFUSED_SERVER_UNAVAILABLE",
            CONNACK_REFUSED_BAD_USERNAME_PASSWORD:"CONNACK_REFUSED_BAD_USERNAME_PASSWORD",
            CONNACK_REFUSED_NOT_AUTHORIZED:"CONNACK_REFUSED_NOT_AUTHORIZED",
        }
        return rc_dict.get(int(rc_code),"Unknown MQTT RC Code")


"""
This emulates the MQTT messaging AND the clearview. 

If you have an ESP32, flash the ESP32 with the software and hook up a serial port.
Then, run the clearview's simulator linked to the serial port
"""
class VRxCV_emulator:
    def __init__(self, protocol_version, serial_num, broker_ip, node_number):
        self._protocol_version = protocol_version
        self._serial_num = serial_num
        self._mqttc = MQTT_Client(client_id=serial_num, 
                                    broker_ip=broker_ip, 
                                    subscribe_topics=mqtt_sub_topics,
                                    node_number=node_number)
        self._add_message_callbacks()
        self._node_number = node_number

    
        try:
            self._mqttc.loop_forever()  # This blocks
            #self._mqttc.loop_start()
        except KeyboardInterrupt:
            self._mqttc.disconnect_gracefully()
        except:
            raise r

    def _on_message_kick(self,client, userdata, message):
        self._mqttc.disconnect_gracefully()

    def _add_message_callbacks(self):

        cv1_topics = mqtt_sub_topics["cv1"]

        callbacks_and_topics = {
            self._on_message_kick: cv1_topics["receiver_kick_topic"]
        }


        for callback in callbacks_and_topics:
            rec_topic = callbacks_and_topics[callback]

            formatter_name = rec_topic[1]
                  
            if formatter_name == "node_number":
                rec_topic = rec_topic[0]%self._node_number
            elif formatter_name == "receiver_serial_num":
                rec_topic = rec_topic[0]%self._serial_num
            elif formatter_name in ["#","*"]:   # subscibe to all at level (*) or recursively all (#)
                rec_topic = rec_topic[0]%formatter_name
            elif formatter_name is None:
                rec_topic = rec_topic[0]
            elif isinstance(rec_topic,tuple):
                raise ValueError("Uncaptured formatter_name: %s"%formatter_name)
            elif isinstance(rec_topic,str):
                pass
            else:
                raise TypeError("rec_topic not of correct type: %s"%rec_topic)
                    
            self.logger.debug("\tBinding callback \n\t\t*Function: 'self.%s'\n\t\t*Topic: '%s'"%(callback.__name__,rec_topic))
            self._mqttc.message_callback_add(rec_topic, 
                                             callback)
        

        

        
        # try:
        #     while True:
        #         pass
        # except KeyboardInterrupt:
        #     self._mqttc.disconnect_gracefully()
        #     # self._mqttc._client.disconnect()
        #     # self._mqttc._client.loop_stop()
        



    




def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s","--serial_number", 
                        default = "CV-UNSET_SERIAL_NUM", 
                        help = "unique serial number")
    parser.add_argument("-a","--address", 
                        default = "localhost", 
                        help = "mqtt broker ip address or hostname")

    args = parser.parse_args()

    vrx = VRxCV_emulator("1.0", args.serial_number,args.address,node_number=0 )
    





if __name__ == "__main__":
    main()

