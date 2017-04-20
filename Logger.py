"""
Rickie Kerndt <rkerndt@cs.uoregon.edu>
Subscribes to all tc\ messages and output message payload to file.
"""

from TC_server import TC, TC_Exception, TC_Identifier, TC_Request_Off, TC_Request_On, TC_ACK
import paho.mqtt.client as mqtt
import socket
from time import sleep
import signal
import sys
from json import JSONDecodeError

class TC_Logger(TC):

    def __init__(self, user_id:str):
        """

        :param controller_id:
        """
        super().__init__()
        self.id = user_id
        self.tc_topic = TC._topic_base + '#'
        self.mqttc = mqtt.Client(user_id)
        self.mqttc.username_pw_set(user_id, password="BikeIoT")
        self.mqttc.user_data_set(self)

        #set all callbacks since we which to log everything seen from the brocker
        self.mqttc.will_set(TC._will_topic, TC_Identifier(TC.WILL, self.id).encode())
        self.mqttc.on_connnect = TC.on_connect
        self.mqttc.on_disconnect = TC.on_disconnect
        self.mqttc.on_message = TC.on_message
        self.mqttc.on_publish = TC.on_publish
        self.mqttc.on_subscribe = TC.on_subscribe
        self.mqttc.on_unsubscribe = TC.on_unsubscribe
        self.mqttc.message_callback_add(self.tc_topic, TC_Logger.on_topic)


    def run(self):
        """

        :return: None
        """

        connected = False
        connection_retry_delay = TC.INITIAL_CONNECTION_RETRY_DELAY
        while not connected:
            try:
                connected = True
                msg = "starting TC Server for controller %s" % (self.id,)
                self.output_log(msg)
                self.mqttc.connect(TC._broker_url, TC._broker_port, TC._broker_keepalive)
            except (socket.gaierror, socket.herror, socket.timeout) as e:
                # probably network initialization delayed at startup, retry with progressive delay
                error_int, error_string = e.args
                connected = False
                msg = "connect attempt failed (%d) %s:retry in %f seconds" % (error_int, error_string, connection_retry_delay)
                self.output_error(msg)
                sleep(connection_retry_delay)
                connection_retry_delay *= TC.CONNECTION_RETRY_FACTOR
                if connection_retry_delay > TC.MAX_CONNECTION_RETRY_DELAY:
                    connection_retry_delay = TC.MAX_CONNECTION_RETRY_DELAY
            except (ConnectionError, ConnectionRefusedError, ConnectionAbortedError, ConnectionResetError) as e:
                error_int, error_string = e.args
                msg = "aborted due to connection error (%d) (%s)" % (error_int, error_string)
                self.output_error(msg)
                exit(error_int)
            except:
                msg = "aborted with unkown error"
                self.output_error(msg)
                exit(1)

        # subscribe to base topic to pick up all messages
        self.mqttc.subscribe(self.tc_topic)

        # enter network loop forever, relying on interrupt handler to stop things
        self.mqttc.loop_forever()

    def stop(self):
        """

        :return: None
        """
        msg = "stopping TC Logger %s" % (self.id,)
        self.output_log(msg)
        self.mqttc.disconnect()

    def signal_handler(self, signum, frame):
        """
        Shuts down Logger on SIGINT and SIGTERM
        :param signum:
        :param frame:
        :return: None
        """
        if signum in [signal.SIGTERM, signal.SIGINT]:
            self.stop()


    @staticmethod
    def on_topic(client, userdata, msg:mqtt.MQTTMessage):
        """
        Prints out a human readable form for messages that are based on TC_Type. Otherwise, prints nothing and debug
        level must be set higher than 1 to see a 'raw' output of all messages.
        :param userdata:
        :param mqtt_msg:
        :return: None
        """


        # only handling PHASE_REQUEST for now, if no match then ignore

        log_msg = None
        request = None
        op = '<unknown>'

        try:
            request_type = TC.get_type(msg.payload)
            if request_type == TC.PHASE_REQUEST_ON:
                request = TC_Request_On.decode(msg)
            elif request_type == TC.PHASE_REQUEST_OFF:
                request = TC_Request_Off.decode(msg)
            elif request_type == TC.ACK:
                request = TC_ACK.decode(msg)
            else:
                # try decoding as a json encoded string
                request = TC.decode_json(msg)
        except TC_Exception as err:
            userdata.output_error(err.msg)
        except JSONDecodeError as err:
            userdata.output_error(err.msg)
        if request:
            userdata.output_log(request)
        else:
            log_msg = "Request decode failed for message %s <%s>" % (msg.mid, msg.payload)
            userdata.output_log(log_msg)

def main(argv):
    """

    :param argv:
    :return: int
    """

    USAGE = "Logger user_id"

    if len(argv) !=2:
        print(USAGE, file=sys.stdout)
        sys.exit(0)

    myLogger = TC_Logger(argv[1])

    signal.signal(signal.SIGTERM, myLogger.signal_handler)
    signal.signal(signal.SIGINT, myLogger.signal_handler)

    myLogger.run()
    sys.exit(0)

if __name__ == '__main__':
    main(sys.argv)

