"""
Rickie Kerndt <rkerndt@cs.uoregon.edu>
Subscribes to all tc\ messages and output message payload to file.
"""

from TC_server import TC, TC_Exception, TC_Identifier
import paho.mqtt.client as mqtt
import socket
from time import sleep
import signal
import sys
from ctypes import *
import threading
import os

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

        self.subscriptions = [(self.tc_topic, TC._qos)]

        #set all callbacks since we which to log everything seen from the brocker
        self.mqttc.will_set(TC._will_topic, TC_Identifier(TC.WILL, self.id).encode())
        self.mqttc.on_connnect = TC.on_connect
        self.mqttc.on_disconnect = TC.on_disconnect
        self.mqttc.on_message = TC.on_message
        self.mqttc.on_publish = TC.on_publish
        self.mqttc.on_subscribe = TC.on_subscribe
        self.mqttc.on_unsubscribe = TC.on_unsubscribe
        self.mqttc.message_callback_add(self.tc_topic, TC_Logger.on_topic)

        # watchdog timer, set watchdog_pid iff running with systemd type=notify
        self._watchdog_timer = None
        self.watchdog_pid = None
        self.watchdog_sec = None

        # load needed dynamic libraries
        self._libsystemd = CDLL("libsystemd.so")


    def run(self):
        """

        :return: None
        """

        #tell systemd we are ready
        result = self._libsystemd.sd_pid_notify(self.watchdog_pid,0,"READY=1".encode('ascii'))
        if result <= 0:
            msg = "Error %d sending sd_pid_notify READY" % (result,)
            self.output_log(msg)

        # initialize watchdog
        if self.watchdog_pid and self.watchdog_sec:
            if self.debug_level > 2:
                msg = "Initializing watchdog timer on pid %d and interval %f seconds" % (self.watchdog_pid,
                        self.watchdog_sec/TC.WATCHDOG_INTERVAL)
                self.output_log(msg)
            self.watchdog()

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
                msg = "aborted with unkown error: %s" % (sys.exc_info()[0],)
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


    def watchdog(self):
        """
        Method sends 'heartbeat' to sd_notfiy(3). When run from systemd will cause system to restart the service.
        This should be called with a period <= WatchdogSec/3. (see systemd.service(8))

        Add features to the method to check on thread status and take corrective actions as needed.
        :return: None
        """

        if self.debug_level > 3:
            msg = "Running watchdog for pid %d, timeout in %d seconds" % (self.watchdog_pid, self.watchdog_sec)
            self.output_log(msg)

        result = 0

        # load the library at run time using cdll
        if self._healthy:
            result = self._libsystemd.sd_pid_notify(self.watchdog_pid,0,"WATCHDOG=1".encode('ascii'))

        if result <= 0:
            msg = "Error (%d) in sd_pid_notify" % (result,)
            self.output_log(msg)
        self._watchdog_timer = threading.Timer(self.watchdog_sec/TC.WATCHDOG_INTERVAL, self.watchdog)
        self._watchdog_timer.start()
        self._healthy = False


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

        request = None

        try:
            request = TC.decode(msg)
        except TC_Exception as err:
            userdata.output_error(err.msg)
        if request:
            log_msg = "[%s] %s" % (msg.topic, request.__str__())
            userdata.output_log(log_msg)
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

    if myLogger._debug_level > 2:
        myPID = os.getpid()
        print("Process ID = %d" % myPID)
        myLogger.watchdog_pid = myPID
        myLogger.watchdog_sec = 10

    if ("WATCHDOG_PID" in os.environ) and os.environ["WATCHDOG_PID"].isdigit():
        myLogger.watchdog_pid = int(os.environ["WATCHDOG_PID"])
        print("watchdog pid = %s" % (myLogger.watchdog_pid,))

    if ("WATCHDOG_USEC" in os.environ) and os.environ["WATCHDOG_USEC"].isdigit():
        myLogger.watchdog_sec = int(os.environ["WATCHDOG_USEC"]) // 1000000
        print("watchdog sec = %s" % (myLogger.watchdog_sec,))


    signal.signal(signal.SIGTERM, myLogger.signal_handler)
    signal.signal(signal.SIGINT, myLogger.signal_handler)

    myLogger.run()
    sys.exit(0)

if __name__ == '__main__':
    main(sys.argv)

