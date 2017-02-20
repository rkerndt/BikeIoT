"""
Rickie Kerndt <rkerndt@cs.uoregon.edu>
Classes and methods for receiving traffic controller phase requests.
"""

try:
    import grovepi
    I_AM_PI = True
except:
    I_AM_PI = False

import paho.mqtt.client as mqtt
import struct
from datetime import datetime, timedelta
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
    PHASE_REQUEST =     0x01
    PHASE_REQUEST_ON =  0x02
    PHASE_REQUEST_OFF = 0x03
    MAX_PHASE_ON_SECS = 0x60

    PHASE_ON =  0x01
    PHASE_OFF = 0x00

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
    _default_phase_map = { 1:2, 2:3, 3:4, 4:5 }
    _phase_dwell = 0.1

    # general payload formats
    _payload_type_format = '!i'
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
        (request_type,) = struct.unpack_from(TC._payload_type_format, payload, 0)
        return request_type

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

class TC_Type:
    """
    Base TC class which holds only the type value
    """
    _struct_format = '!i'
    _struct_size = struct.calcsize(_struct_format)

    def __init__(self, type):
        """
        No reason to create this base type, use decode() to obtain type value from a derived class. But, this
        would be better done using get_type() method in class TC.
        """
        self.type = type

    def encode(self):
        """
        Converts type into a bytes object represent the c structure:
        struct TC_Type {
            int type;
        } __attribute__((PACKED));
        :return: bytearray
        """
        packed = struct.pack(TC_Type._struct_format, self.type)
        return bytearray(packed)

    @classmethod
    def decode(cls, payload:bytes):
        """
        Creates a TC_Type object from bytes object which should have been packed using encode() method
        from TC_Type derived object.
        :return: TC_Type
        """
        if len(payload) < TC_Type._struct_size:
            msg = 'improperly formatted TC Type (derived) payload'
            raise TC_Exception(msg)
        (type,) = struct.unpack_from(TC_Type._struct_format, payload, 0)
        return TC_Type(type)

class TC_Identifier(TC_Type):
    """
    Structure for TC identifier payload. Includes just the type and sender fields. This class is used for the
    will payload (with type set to TC.Will. All other payload types are derived from this class
    """
    _struct_format = '!i%ds' % (TC.MAX_ID_BYTES,)
    _struct_size = struct.calcsize(_struct_format)

    def __init__(self, type:int, id:str):
        """

        :param id: str
        """
        super().__init__(type)
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
        packed = struct.pack(TC_Identifier._struct_format, self.type, id_bytes)
        return bytearray(packed)

    @classmethod
    def decode(cls, payload:bytes):
        """
        Creates a TC_Identifier object from bytes object which should have been packed using TC_Identifier.encode()
        or encoded for a derived class.
        :return: TC_Identifier object
        """
        if len(payload) < TC_Identifier._struct_size:
            msg = 'improperly formatted TC Will payload'
            raise TC_Exception(msg)
        type, id_bytes = struct.unpack_from(TC_Identifier._struct_format, payload, 0)
        id = id_bytes.decode()
        return TC_Identifier(type, id)


class TC_Request(TC_Identifier):
    """
    Structure and methods for manipulating mqtt payloads used in traffic control requests
    """

    _struct_format = '!i%ds%dsii' % (TC.MAX_ID_BYTES, TC.MAX_ID_BYTES)
    _struct_size = struct.calcsize(_struct_format)

    def __init__(self, user_id: str, controller_id: str, phase: int, arrival_time:int=0):
        """
        Instantiates a Traffic Controller phase request
        :param user_id: str
        :param controller_id: str
        :param phase: int
        :param arrival_time: int (Seconds until arrival)
        """
        super().__init__(TC.PHASE_REQUEST, user_id)
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
        user_id_bytes = self.id.encode('utf-8')
        controller_id_bytes = self.controller_id.encode('utf-8')
        if len(user_id_bytes) > TC.MAX_ID_BYTES:
            msg = "user id <%s> exceeds %d utf-8 bytes" % (self.id, TC.MAX_ID_BYTES)
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


class TC_Request_On(TC_Request):
    """
    TC_Request mqtt payload to set phase on
    """

    def __init__(self, user_id: str, controller_id: str, phase: int, arrival_time:int=0):
        """

        :param user_id:
        :param controller_id:
        :param phase:
        :param arrival_time:
        """
        super().__init__(user_id, controller_id, phase, arrival_time)
        self.type = TC.PHASE_REQUEST_ON

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

        if type != TC.PHASE_REQUEST_ON:
            msg = 'payload claimed to be a phase request on but received code (%d)' % type
            raise TC_Exception(msg)
        user_id = user_id_bytes.decode()
        controller_id = controller_id_bytes.decode()

        return TC_Request_On(user_id, controller_id, phase, arrival_time)


class TC_Request_Off(TC_Request):
    """
    TC_Request mqtt payload to set phase on
    """

    def __init__(self, user_id: str, controller_id: str, phase: int, arrival_time: int = 0):
        """

        :param user_id:
        :param controller_id:
        :param phase:
        :param arrival_time:
        """
        super().__init__(user_id, controller_id, phase, arrival_time)
        self.type = TC.PHASE_REQUEST_OFF

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

        if type != TC.PHASE_REQUEST_OFF:
            msg = 'payload claimed to be a phase request off but received code (%d)' % type
            raise TC_Exception(msg)
        user_id = user_id_bytes.decode()
        controller_id = controller_id_bytes.decode()

        return TC_Request_Off(user_id, controller_id, phase, arrival_time)

class TC_Pin_State:
    """
    State information we want to keep of a phase loop
    """

    def __init__(self, pin_num):
        self.num = pin_num
        self.last_set = datetime.now()
        self.state = TC.PHASE_OFF


class TC_Relay(threading.Thread):
    """
    Controls relays effecting Traffic Controller Phases. Maintains local phase state and setter methods that ensure
    relayy access methods are executed atomically.
    """

    def __init__(self, pins, max_on_time=TC.MAX_PHASE_ON_SECS):
        """
        Sets up control of these pins, relies on server to provide a valid gpio pin list
        A timer is setup to check states every 30 seconds. This allows PHASE_ON to timeout
        after TC.MAX_PHASE_ON_SECS. Acts as a fail safe so that states are not kept on
        indefinitely.
        :param self:
        :param pins: list of grovepi pin ids used for relay control
        :return: None
        """
        super().__init__()
        self._max_on_time = max_on_time
        self._valid_pins = frozenset(pins)
        self._pin_states = dict()
        self._runnable = True
        self._lock = threading.Lock()
        self._update = threading.Event()
        self._timer = threading.Timer(TC.MAX_PHASE_ON_SECS/2, self._timeout)

        for pin in pins:
            self._pin_states[pin] = TC_Pin_State(pin)

    def set_phase_on(self, pin):
        """
        Sets the state of the pin to on
        :param pin:
        :return: None
        """
        print("entered set_phase_on")
        self._lock.acqurie()
        print("set_phase_on acquired lock")
        self._timer.cancel()
        if pin in self._valid_pins:
            pin_state = self._pin_states[pin]
            pin_state.state= TC.PHASE_ON
            pin_state.last_set = datetime.now()
        self._update.set()
        self._timer = threading.Timer(TC.MAX_PHASE_ON_SECS/2, self._timeout)
        self._lock.release()
        print("set_phase_on released lock")

    def set_phase_off(self, pin):
        """
        Sets the state of pin to off
        :param pin:
        :return: None
        """
        self._lock.acquire()
        self._timer.cancel()
        if pin in self._valid_pins:
            pin_state = self._pin_states[pin]
            pin_state.state = TC.PHASE_OFF
            pin_state.last_set = datetime.now()
        self._update.set()
        self._timer = threading.Timer(TC.MAX_PHASE_ON_SECS/2, self._timeout)
        self._lock.release()

    def stop(self):
        """
        Quits thread
        :return: None
        """
        self._runnable = False

    def run(self):
        """

        :return: None
        """
        while self._runnable:
            self._update.wait()
            self._check_states()


    def _timeout(self):
        """
        Calls _check_states and resets the timer
        :return: None
        """
        self._check_states()
        self._timer = threading.Timer(TC.MAX_PHASE_ON_SECS/2, self._timeout)

    def _check_states(self):
        """
        Passes through pin states making gpio calls to set relay to the corresponding state
        :return: None
        """

        self._lock.acquire()
        self._update.clear()
        for pin_state in self._pin_states:
            if pin_state.state == TC.PHASE_ON:
                # turn off if exceed max time on
                if (datetime.now() - pin_state.last_set) > timedelta(seconds=TC.MAX_PHASE_ON_SECS):
                    pin_state.state = TC.PHASE_OFF

            # TODO: check against actual gpio pin state rather than just setting
            # TODO: also need to add confirmation that write was successful
            value = 0
            if pin_state.state == TC.PHASE_ON:
                value = 1
            grovepi.digitalWrite(pin_state.num, value)
        self._lock.release()

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
        if not I_AM_PI:
            msg = "class Server is only supported on Raspberry Pi with RPi._grovepi and grovepi installed"
            raise TC_Exception(msg)

        super().__init__()
        self.id = controller_id
        self.tc_topic = TC._tc_topic_format % (self.id,)
        self.phase_to_gpio = dict(map)
        self.phases = frozenset(self.phase_to_gpio.keys())

        self.mqttc = mqtt.Client(controller_id)

        # Separate thread to manage TC relays
        self._relays = TC_Relay(self.phase_to_gpio.values())

        # using password until we can get TLS setup with user certificates
        self.mqttc.username_pw_set(self.id)

        # pass reference to self for use in callbacks
        self.mqttc.user_data_set(self)

        # defined required topic callbacks
        self.mqttc.will_set(TC._will_topic, TC_Identifier(TC.WILL, self.id).encode())
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
        self._relays.start()
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
        self._relays.stop()
        self.mqttc.disconnect()
        self._relays.join()

    def request_phase(self, request:TC_Request):
        """
        Process phase request to signal traffic controller
        :param request:TC_Request
        :return: None
        """

        if request.phase in self.phases:
            msg = "processing request type %d for phase %d from %s in %d seconds" % (request.type, request.phase, request.id, request.arrival_time)
            self.output_log(msg)
            if request.type == TC.PHASE_REQUEST_ON:
                self._relays.set_phase_on(self.phase_to_gpio[request.phase])
                msg = "set phase %d to on for %s" % (request.phase, request.id)
                self.output(msg)
            elif request.type == TC.PHASE_REQUEST_OFF:
                self._relays.set_phase_off(self.phase_to_gpio[request.phase])
                msg = "set phase %d to off for %s" % (request.phase, request.id)
                self.output(msg)
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

        msg = "received message id %s on topic %s" % (mqtt_msg.mid, mqtt_msg.topic)
        userdata.output_log(msg)

        # only handling PHASE_REQUEST for now, if no match then ignore
        try:
            request_type = Server.get_type(mqtt_msg.payload)
            if request_type == TC.PHASE_REQUEST_ON:
                request = TC_Request_On.decode(mqtt_msg.payload)
                userdata.request_phase(request)
            elif request_type == TC.PHASE_REQUEST_OFF:
                request = TC_Request_Off.decode(mqtt_msg.payload)
                userdata.request_phase(request)
            else:
                msg = "received payload of type %d but expecting %d" % (request_type, TC.PHASE_REQUEST)
                userdata.output_error(msg)
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
        self.mqttc.will_set(TC._will_topic, TC_Identifier(TC.WILL, self.id).encode())
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

        # subscribe to will topic to get messages intended for me
        self.mqttc.subscribe(TC._will_topic, TC._qos)


        # start network loop
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
        Creates a TC_Request_On object and publishes on the appropriate topic
        :param controller_id: str
        :param phase: int
        :param arrival_time: int
        :return: None
        """
        request = TC_Request_On(self.id, controller_id, phase, arrival_time)
        topic = TC._tc_topic_format % controller_id
        msg = "sending reqeust to %s for phase %d in %d seconds" % (controller_id, phase, arrival_time)
        self.output_log(msg)
        self.mqttc.publish(topic, request.encode())

    def send_phase_release(self, controller_id:str, phase:int, departure_time:int=0):
        """
        Creates a TC_Reqeust_Off object and publishes on the appropriate topic
        :param controller_id:
        :param phase:
        :param departure_time:
        :return: None
        """
        request = TC_Request_Off(self.id, controller_id, phase, departure_time)
        topic = TC._tc_topic_format % controller_id
        msg = "sending reqeust to %s for phase %d in %d seconds" % (controller_id, phase, departure_time)
        self.output_log(msg)
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






