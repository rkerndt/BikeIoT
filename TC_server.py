"""
Rickie Kerndt <rkerndt@cs.uoregon.edu>
Classes and methods for receiving traffic controller phase requests.
"""

import paho.mqtt.client as mqtt
import grovepi
import struct
from datetime import datetime
import sys
import threading
from time import sleep
import signal

class TC_Exception (Exception):
    """
    Class for catching error messages.
    """
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg

    def __repr__(self):
        return "TC_Exception(\"%s\")" % (self.msg,)

class TC:
    """
    Base class to hold some common attributes and methods between Server and User derived classes
    """

    # Constants
    WILL = 0x00
    PHASE_REQUEST = 0x01
    MAX_ID_BYTES = 64      # maximum identifer length after utf-8 conversion

    # CONNACK codes: returned in rc of on_connect
    CONNACK_LOOKUP = {mqtt.CONNACK_ACCEPTED:'successful connection',
                      mqtt.CONNACK_REFUSED_PROTOCOL_VERSION:'failed due to incorrect protocol version',
                      mqtt.CONNACK_REFUSED_IDENTIFIER_REJECTED:'failed due to rejected identifier',
                      mqtt.CONNACK_REFUSED_SERVER_UNAVAILABLE:'failed due to unavailable server',
                      mqtt.CONNACK_REFUSED_BAD_USERNAME_PASSWORD:'failed due to bad username or password',
                      mqtt.CONNACK_REFUSED_NOT_AUTHORIZED:'failed due to not authorized'}

    # configuration: TODO: put this stuff into a configuration file
    _qos = 2
    _topic_base = 'tc/'
    _will_topic =  _topic_base + 'will/'
    _tc_topic_format = _topic_base + '%s/'
    _broker_url = 'julie.eug.kerndt.com'
    _broker_port = 1883
    _broker_keepalive = 60
    _default_phase_map = { 1:3, 2:4, 3:4, 4:5 }
    _phase_dwell = 0.1

    # general payload formats
    _payload_type_format = '!I'
    _payload_type_length = struct.calcsize(_payload_type_format)

    def __init__(self):
        self.lock = threading.Lock()

    def output_error(self, msg:str):
        """
        Prints timestamp and message to stderr
        :param msg:str
        :return: None
        """
        print("%s %s" % (datetime.now(), msg), file=sys.stderr)

    def output_log(self, msg:str):
        """
        Prints timestamp and message to stdout
        :param msg: str
        :return: None
        """
        print("%s %s" % (datetime.now(), msg), file=sys.stderr)

    def start(self):
        """
        Tasks to connect to broker and begin network loop. Must be redefined
        :return: None
        """
        msg = 'unimplemented start() method called'
        raise TC_Exception(msg)

    def stop(self):
        """
        Tasks to stop operations and disconnect from the broker. Must be redefined
        :return: None
        """
        msg = 'unimplemented stop() method called'
        raise TC_Exception(msg)

    @staticmethod
    def get_type(payload:bytes):
        """
        Examines the first field within the packed byte object to obtain the payload type value.
        :param payload:
        :return: int
        """
        if len(payload) < TC._payload_type_length:
            msg = 'improperly formated TC payload'
            raise TC_Exception(msg)
        return struct.unpack_from(TC._payload_type_format, payload, 0)

    """
    The following static methods are signatures for the various mqtt callback functions.
    """

    @staticmethod
    def on_will(client, userdata, mqtt_msg):
        """
        Called when a will topic is received notifying that a peer has died.
        :param client: paho.mqtt.client
        :param userdata: TC Server of Client handling callback
        :param mqtt_msg:
        :return: None
        """
        pass

    @staticmethod
    def on_topic(client, userdata, mqtt_msg):
        """
        Called when message is received on Servers primary topic. This must be defined to be called when
        receiving message on topic defined as TC._tc_topic_format % controller_id.
        :param client:
        :param userdata:
        :param mqtt_msg:
        :return:
        """
        msg = 'unimplemented on_topic() method called'
        raise TC_Exception(msg)

    @staticmethod
    def on_connect(client, userdata, flags, rc):
        """
        Called when the broker responds to our connection request
        :param client: paho.mqtt.client
        :param userdata: TC Server or Client handling callback
        :param flags: dict of broker response flags
        :param rc: int connection result
        :return: None
        """
        msg = TC.CONNACK_LOOKUP[rc]
        if rc == mqtt.CONNACK_ACCEPTED:
            userdata.output_log(msg)
        else:
            userdata.output_error(msg)
            userdata.stop()


    @staticmethod
    def on_disconnect(client, userdata, flags, rc):
        """
        Called when the client disconnects from the broker
        :param client: paho.mqtt.client
        :param userdata: TC Server or Client handling callback
        :param flags: dict of broker response flags
        :param rc: int disconnect result
        :return: None
        """
        pass

    @staticmethod
    def on_message(client, userdata, mqtt_msg):
        """
        Called when a message has been received on a topic that the client subscribes to. This callback will be
        called for every message received. Use message_callback_add() to define multiple callbacks that will be
        called for specific topic filters.
        :param client: paho.mqtt.client
        :param userdata: TC Server or Client handling callback
        :param mqtt_msg: MQTTMessage
        :return: None
        """
        msg = "received message id %d" % (mqtt_msg.mid,)
        userdata.output_log(msg)

    @staticmethod
    def on_publish(client, userdata, mqtt_mid):
        """
        Called when a message that was to be sent using publish() call has completed transmission to the broker.
        For messages with QoS levels 1 and 2, this means that the appropriate handshakes have completed. For QoS 0,
        this simply means that the message has left the client. The mqtt_mid variable matches the mid variable returned
        from the corresponding publish() call, to allow outgoing messages to be tracked.
        This callback is important because even if the publish() call returns success, it does not always mean
        that the message has been sent.
        :param client: paho.mqtt.client
        :param userdata: TC Server or Client handling callback
        :param mqtt_mid: MQTTMessage.mid
        :return: None
        """
        msg = "published message id %d" % (mqtt_mid,)
        userdata.output_log(msg)

    @staticmethod
    def on_subscribe(client, userdata, mqtt_mid, granted_qos):
        """
        Called when the broker responds to a subscribe request. The mqtt_mid vriable matches the mid variable
        returned from the corresponding subscribe() call. The granted_qos variable is a list of integers that
        give the QoS level the broker has granted for each of the different subscription requests.
        :param client: paho.mqtt.client
        :param userdata: TC Server or Client handling callback
        :param mqtt_mid: MQTTMessage.mid
        :return: None
        """
        msg = "subscribe granted for message %d with qos %s" % (mqtt_mid, str(granted_qos))
        userdata.output_log(msg)

    @staticmethod
    def on_unsubscribe(client, userdata, mqtt_mid):
        """
        Called when the broker responds to an unsubscribe request. The mqtt_mid variable matches the mid variable
        returned from the corresponding unsubscribe() call.
        :param client: paho.mqtt.client
        :param userdata: TC Server or Client handling callback
        :param mqtt_mid: MQTTMessage.mid
        :return: None
        """
        pass

    @staticmethod
    def on_log(client, userdata, level, buf):
        """
        Called when the client has log information. Define to allow debugging.
        :param client: paho.mqtt.client
        :param userdata: TC Server or Client handling callback
        :param level: MQTT_LOG_INFO, MQTT_LOG_NOTICE, MQTT_LOG_WARNING, MQTT_LOG_ERR, MQTT_LOG_DEBUG
        :param buf: bytes The actual message
        :return: None
        """
        pass

class TC_Will():
    """
    Structure for TC will payload. Sent by broker when a client has 'died'.
    """
    _struct_format = '!I%ds' % (TC.MAX_ID_BYTES,)
    _struct_size = struct.calcsize(_struct_format)

    def __init__(self, id:str):
        """

        :param id: str
        """
        self.type = TC.WILL
        self.id = id

    def encode(self):
        """
        Converts will into a bytes object represent the c structure:
        struct TC_Will {
            int type;
            char id[TC.MAX_ID_BYTES];
        }  __attribute__((PACKED));
        :return: bytearray
        """
        id_bytes = self.id.encode('utf-8')
        if len(id_bytes) > TC.MAX_ID_BYTES:
            msg = "user id<%s> exceeds %d utf-8 bytes" % (self.id, TC.MAX_ID_BYTES)
            raise TC_Exception(msg)
        packed = struct.pack(TC_Will._struct_format, self.type, id_bytes)
        return bytearray(packed)

    @classmethod
    def decode(cls, payload:bytes):
        """
        Creates a TC_Will object from bytes object which should have been packed using TC_Will.encode()
        :return: TC_Will object
        """
        if len(payload) != TC_Will._struct_size:
            msg = 'improperly formatted TC Will payload'
            raise TC_Exception(msg)
        type, id_bytes = struct.unpack(TC_Will._struct_format, payload)
        id = id_bytes.decode()
        return TC_Will(id)


class TC_Request():
    """
    Structure and methods for manipulating mqtt payloads used in traffic control requests
    """

    _struct_format = '!I%ds%dsII' % (TC.MAX_ID_BYTES, TC.MAX_ID_BYTES)
    _struct_size = struct.calcsize(_struct_format)

    def __init__(self, user_id: str, controller_id: str, phase: int, arrival_time:int=0):
        """
        Instantiates a Traffic Controller phase request
        :param user_id: str
        :param controller_id: str
        :param phase: int
        :param arrival_time: int (Seconds until arrival)
        """
        self.type = TC.PHASE_REQUEST
        self.user_id = user_id
        self.controller_id = controller_id
        self.phase = phase
        self.arrival_time = arrival_time

    def encode(self):
        """
        Converts python values into a bytes object representing a c structure for use in mqtt payload. Strings
        are encoded as a utf-8 bytes object and packed as a char[].

        struct TC_Request {
            int type;
            char user_id[TC.MAX_ID_BYTES];
            char controller_id[TC.MAX_ID_BYTES];
            int phase;
            int arrival_time;
            } __attribute__((PACKED));

        :return: bytearray
        """
        user_id_bytes = self.user_id.encode('utf-8')
        controller_id_bytes = self.controller_id.encode('utf-8')
        if len(user_id_bytes) > TC.MAX_ID_BYTES:
            msg = "user id <%s> exceeds %d utf-8 bytes" % (self.user_id, TC.MAX_ID_BYTES)
            raise TC_Exception(msg)
        if len(controller_id_bytes) > TC.MAX_ID_BYTES:
            msg = "controller id <%s> exceeds %d utf-8 bytes" % (self.controller_id, TC.MAX_ID_BYTES)
            raise TC_Exception(msg)
        packed = struct.pack(TC_Request._struct_format, self.type, user_id_bytes, controller_id_bytes,
                             self.phase,self.arrival_time)
        return bytearray(packed)


    @classmethod
    def decode(cls, payload:bytes):
        """
        Creates a TC_Request object from bytes objects which should have been packed using
        TC_Request.encode()

        :param payload: bytes
        :return: TC_Request
        """
        if len(payload) != TC_Request._struct_size:
            msg = 'improperly formatted TC Request payload'
            raise TC_Exception(msg)

        type, user_id_bytes, controller_id_bytes, phase, arrival_time = struct.unpack(TC_Request._struct_format, payload)

        if type != TC.PHASE_REQUEST:
            msg = 'payload claimed to be a phase request but received code (%d)' % type
            raise TC_Exception(msg)
        user_id = user_id_bytes.decode()
        controller_id = controller_id_bytes.decode()

        return TC_Request(user_id, controller_id, phase, arrival_time)

class Server (TC):
    """
    Traffic controller server for receiving phase requests from mqtt clients.
    TODO: add locking so only one request is processed at a time, how to deal with heavy load
    """

    def __init__(self, controller_id:str, map=TC._default_phase_map):
        """
        Instantiates traffic controller server
        :param controller_id: str
        :param map: list [(int,int)] or dict {int:int} mapping of phase number to gpio pin (using grovepi pin numbers)
        """
        super().__init__()
        self.id = controller_id
        self.tc_topic = TC._tc_topic_format % (self.id,)
        self.phase_to_gpio = dict(map)
        self.phases = frozenset(self.phase_to_gpio.keys())

        self.mqttc = mqtt.Client(controller_id)

        # using password until we can get TLS setup with user certificates
        self.mqttc.username_pw_set(self.id)

        # pass reference to self for use in callbacks
        self.mqttc.user_data_set(self)

        # defined required topic callbacks
        self.mqttc.will_set(TC._will_topic, TC_Will(self.id).encode())
        self.mqttc.on_connect = TC.on_connect
        self.mqttc.on_subscribe = TC.on_subscribe
        self.mqttc.on_message = TC.on_message
        self.mqttc.message_callback_add(TC._will_topic, Server.on_will)
        self.mqttc.message_callback_add(self.tc_topic, Server.on_topic)

    def run(self):
        """
        Connects to broker and begins loop.
        TODO: Needs some error handling, response to connect and subscribe. What happens if client disconnects?
        :return: None
        """

        self.mqttc.connect(TC._broker_url, TC._broker_port, TC._broker_keepalive)

        # subscribe to own controller_id topic and will topic to get messages intended for me
        self.mqttc.subscribe([(self.tc_topic, TC._qos), (TC._will_topic, TC._qos)])

        # enter network loop forever, relying on interrupt handler to stop things
        msg = "starting TC Server for controller %s" % (self.id,)
        self.output_log(msg)
        self.mqttc.loop_forever()

    def stop(self):
        """
        Meant to be called from an interrupt handle to shutdown the Server. It for now just disconnects from
        the broker, causing the nework loop_forever to exit.
        :return: None
        """
        msg = "stopping TC Server for controller %s" % (self.id,)
        self.output_log(msg)
        self.mqttc.disconnect()

    def request_phase(self, request:TC_Request):
        """
        Process phase request to signal traffic controller
        :param request:TC_Request
        :return: None
        """

        if request.phase in self.phases:
            msg = "received request from phase %d from %s" % (request.phase, request.user_id)
            self.output_log(msg)
            self.lock.acquire()
            grovepi.digital_write(self.phase_to_gpio[request.phase], 1)
            sleep(TC._phase_dwell)
            grovepi.digital_write(self.phase_to_gpio[request.phase], 0)
            self.lock.release()

        else:
            msg = "received an invalid phase number %d" % (request.phase,)
            self.output_error(msg)

    @staticmethod
    def on_topic(client:mqtt.Client, userdata, mqtt_msg:mqtt.MQTTMessage):
        """
        Handles all requests coming to server (aka traffic controller)
        :param: client: mqtt.Client
        :param userdata: TC Server
        :param mqtt_msg: MQTTMessage
        :return: None
        """

        # only handling PHASE_REQUEST for now, if no match then ignore
        try:
            type = Server.get_type(mqtt_msg.payload)
            if type == TC.PHASE_REQUEST:
                request = TC_Request.decode(mqtt_msg.payload)
                userdata.request_phase(request)
        except TC_Exception as err:
            userdata.output_error(err.msg)

    def signal_handler(self, signum, frame):
        """
        Shuts down server on SIGINT and SIGTERM
        :param signum:
        :param frame:
        :return: None
        """
        if signum in [signal.SIGTERM, signal.SIGINT]:
            self.stop()

class User(TC):
    """
    User which is going to send traffic controller phase requests
    """

    def __init__(self, user_id:str):
        """

        :param user_id:str
        :param map: list [(int,int)] or dict {int:int} mapping of phase number to gpio pin (using grovepi pin numbers)
        """
        super().__init__()
        self.id = user_id
        self.mqttc = mqtt.Client(user_id)

        # using password until we can get TLS setup with user certificates
        self.mqttc.username_pw_set(self.id)

        # pass reference to self for use in callbacks
        self.mqttc.user_data_set(self)

        # defined required topic callbacks
        self.mqttc.will_set(TC._will_topic, TC_Will(self.id).encode())
        self.mqttc.on_connect = TC.on_connect
        self.mqttc.on_subscribe = TC.on_subscribe
        self.mqttc.on_message = TC.on_message
        self.mqttc.on_publish = TC.on_publish
        self.mqttc.message_callback_add(TC._will_topic, Server.on_will)

    def start(self):
        """
        Connects to broker and enters loop_forever. Use stop() call to terminate connection to broker and
        terminate loop.
        :return: None
        """
        self.mqttc.connect(TC._broker_url, TC._broker_port, TC._broker_keepalive)


        # enter network loop forever, relying on interrupt handler to stop things
        msg = "starting TC User with id %s" % (self.id,)
        self.output_log(msg)
        self.mqttc.loop_start()

    def stop(self):
        """
        Disconnects from broker which will also cause loop_forever to exit in start method.
        :return: None
        """
        self.mqttc.loop_stop()
        self.mqttc.disconnect()

    def send_phase_request(self, controller_id:str, phase:int, arrival_time:int=0):
        """
        Creates a TC_Request object and publishes on the appropriate topic
        :param controller_id: str
        :param phase: int
        :param arrival_time: int
        :return: None
        """
        request = TC_Request(self.id, controller_id, phase, arrival_time)
        topic = TC._tc_topic_format % controller_id
        self.mqttc.publish(topic, request.encode())

def main(argv):
    """
    Main method to run this Server under systemd
    :param argv:
    :return: int
    """

    USAGE = "TC_server controller_id"

    if len(argv) != 2:
        print(USAGE, file=sys.stdout)
        sys.exit(0)

    myTC = Server(argv[1])

    signal.signal(signal.SIGTERM, myTC.signal_handler)
    signal.signal(signal.SIGINT, myTC.signal_handler)

    myTC.run()
    sys.exit(0)

if __name__ == '__main__':
    main(sys.argv)






