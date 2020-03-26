#########################
# Established MQTT Topics
#########################

    ### ClearView Topics v1 ###
        # Publish Topics

# Send command to all receivers
receiver_command_all = "rx/cv1/cmd_all" 

# Send command to a node_number
receiver_command_node_topic = "rx/cv1/cmd_node/%s" # node_number

# Send command to a specific receiver
receiver_command_targeted_topic = "rx/cv1/cmd_target/%s" # receiver_serial_num

# Make a request to all nodes at a node number (all nodes reply)
receiver_request_node_all_topic = "rx/cv1/req_node_all"

# Make a request to a specific node number (the active node replies)
receiver_request_node_active_topic = "rx/cv1/req_node_active/%s" # node number

# Make a request to a specific receiver
receiver_request_targeted_topic = "rx/cv1/req_target/%s" # receiver_serial_num

        # Subscribe Topics

# Response for all
receiver_response_all = "rx/cv1/resp_all"

# Response for a node number
receiver_response_node_topic = "rx/cv1/resp_node/%s" # node_number

mqtt_publish_topics = {
    "cv1" :
        {
            "receiver_command_all":receiver_command_all,
            "receiver_command_node_topic":receiver_command_node_topic,
            "receiver_command_targeted_topic":receiver_command_targeted_topic,
            "receiver_request_node_all_topic":receiver_request_node_all_topic,
            "receiver_request_node_active_topic":receiver_request_node_active_topic,
            "receiver_request_targeted_topic":receiver_request_targeted_topic
        }
}

mqtt_subscribe_topics = {
    "cv1" :
        {
            "receiver_response_all",receiver_response_all,
            "receiver_response_node_topic",receiver_response_node_topic
        }
}