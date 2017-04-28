"""
Rickie Kerndt <rkerndt@cs.uoregon.edu>
Classes and methods for receiving traffic conroller phase requests
"""

import TC_server as TC
import paho.mqtt.client as mqtt


WIFI_ADHOC_CONF = 'wpa_adhoc.conf'
WIFI_CONF_DIR = '/etc/wpa_supplicant'

def reboot():
    """
    
    :return: 
    """
    pass

def wifi_enable(configuration:str):
    """
    
    :param configuration: 
    :return: 
    """
    pass

def wifi_disable():
    """
    
    :param configuration: 
    :return: 
    """
    pass

def upgrade():
    """
    
    :return: 
    """
    pass


def on_admin(client:mqtt.Client, userdata:TC.Server, msg:mqtt.MQTTMessage):
    """
    Callback function to process admin commands
    :param client: 
    :param userdata: 
    :param msg: 
    :return: 
    """

    tc_cmd = None
    rc = TC.TC.ACK_OK

    try:
        tc_cmd = TC.TC.decode(msg)

        # check that command is intended for this server
        if tc_cmd.controller_id != userdata.id:
            rc = TC.TC.ACK_INVALID_CMD
            msg = 'Received command type %d intended for controler %s' % (tc_cmd.type, tc_cmd.controller_id)
            raise TC.TC_Exception(msg)

        if tc_cmd.type == TC.TC.ADMIN_REBOOT:
            userdata.send_ack(tc_cmd, TC.TC.ACK_OK)
            reboot()
        elif tc_cmd.type == TC.TC.ADMIN_WIFI_ENABLE:
            wifi_enable(WIFI_ADHOC_CONF)
            userdata.send_ack(tc_cmd, TC.TC.ACK_OK)
        elif tc_cmd.type == TC.TC.ADMIN_WIFI_DISABLE:
            wifi_disable()
            userdata.send_ack(tc_cmd, TC.TC.ACK_OK)
        else:
            raise TC.TC_Exception('Unexpected command type %d' % tc_cmd.type)

    except TC.TC_Exception as err:
        if tc_cmd:
            if rc == TC.TC.ACK_OK:
                rc = TC.TC.ACK_UNKNOWN_ERR
            userdata.send_ack(tc_cmd, rc)
        userdata.output_error(err.msg)