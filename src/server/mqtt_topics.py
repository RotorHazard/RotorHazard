#########################
# Established MQTT Topics
#########################

# These topics contain the topic headers and then what variables are substituted in later.
# If the topic doesn't have any substitute params, 2nd param is None

    ### ClearView Topics v1 ###
        # Publish Topics

# Send command to all receivers
receiver_command_all = ("rx/cv1/cmd_all", None)

# Send command to a seat_number
receiver_command_seat_topic = ("rx/cv1/cmd_seat/%d","seat_number")

# Send command to a specific receiver
receiver_command_targeted_topic = ("rx/cv1/cmd_target/%s","receiver_serial_num")

# Send a kick command to a specific receiver (leave the network)
receiver_kick_topic = ("rx/cv1/kick/%s","receiver_serial_num")

# Send an active promotion or demotion to a specific receiver
receiver_active_topic = ("rx/cv1/active/%s","receiver_serial_num")

# Make a request to all receivers (all receivers reply)
receiver_request_all_topic = ("rx/cv1/req_all", None)

# Make a request to all seats at a seat number (all seats at that seat_number reply)
receiver_request_seat_all_topic = ("rx/cv1/req_seat_all/%d", "seat_number")

# Make a request to the active seat at a seat index
# Only the active receiver at that seat replies
receiver_request_seat_active_topic = ("rx/cv1/req_seat_active/%d", "seat_number")

# Make a request to a specific receiver
receiver_request_targeted_topic = ("rx/cv1/req_target/%s","receiver_serial_num")

# All command topic for ESP commands
receiver_command_esp_all = ("rx/cv1/cmd_esp_all", None)

# Send command to a seat_number
receiver_command_esp_seat_topic = ("rx/cv1/cmd_esp_seat/%d","seat_number")

# Send command to a specific receiver
receiver_command_esp_targeted_topic = ("rx/cv1/cmd_esp_target/%s","receiver_serial_num")



        # Subscribe Topics

# Response for all
receiver_response_all_topic = ("rx/cv1/resp_all", None)

# Response for a seat number
receiver_response_seat_topic = ("rx/cv1/resp_seat/%s", "+")

# Response for a specific recevier
receiver_response_targeted_topic = ("rx/cv1/resp_target/%s", "+")

# Connection status for receivers
receiver_connection_topic = ("rxcn/%s", "+")

# Receiver static status
receiver_status_static_topic = ("status_static/%s", "+")

# Request variable status
receiver_status_variable_topic = ("status_variable/%s", "+")

mqtt_publish_topics = {
    "cv1" :
        {
            "receiver_command_all":receiver_command_all,
            "receiver_command_seat_topic":receiver_command_seat_topic,
            "receiver_command_targeted_topic":receiver_command_targeted_topic,
            "receiver_request_all_topic":receiver_request_all_topic,
            "receiver_request_seat_all_topic":receiver_request_seat_all_topic,
            "receiver_request_seat_active_topic":receiver_request_seat_active_topic,
            "receiver_request_targeted_topic":receiver_request_targeted_topic,
            "receiver_kick_topic":receiver_kick_topic,
            "receiver_command_esp_all": receiver_command_esp_all,
            "receiver_command_esp_seat_topic":receiver_command_esp_seat_topic,
            "receiver_command_esp_targeted_topic": receiver_command_esp_targeted_topic,
        }
}

mqtt_subscribe_topics = {
    "cv1" :
        {
            "receiver_response_all":receiver_response_all_topic,
            "receiver_response_seat":receiver_response_seat_topic,
            "receiver_connection":receiver_connection_topic,
            "receiver_response_targeted":receiver_response_targeted_topic,
            "receiver_static_status":receiver_status_static_topic,
            "receiver_variable_status":receiver_status_variable_topic
        }
}

ESP_COMMANDS = {
    "Request Static Status": "status_static?",
    "Request Variable Status": "status_var?",
    "Set Node Number": "seat_number=%d",
}