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
import socket
from io import StringIO
import json

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

    # Message Types
    WILL = 0x00
    PHASE_REQUEST =     0x01
    PHASE_REQUEST_ON =  0x02
    PHASE_REQUEST_OFF = 0x03
    ACK = 0x04
    ID = 0x05

    # Constants
    MAX_PHASE_ON_SECS = 0x30
    CONNECTION_RETRY_FACTOR = 2
    INITIAL_CONNECTION_RETRY_DELAY = 0.1
    MAX_CONNECTION_RETRY_DELAY = 60
    DEFAULT_QOS = 2
    CHECK_PENDING_INTERVAL = 1
    CHECK_PHASE_TIMEOUT_INTERVAL = 4
    PHASE_ON =  0x01
    PHASE_OFF = 0x00

    MAX_ID_BYTES = 64      # maximum identifer length after utf-8 conversion
    TC_REQUEST_LENGTH = 4  # for json encoded objects
    TC_ACK_LENGTH = 4

    # encodings
    ENCODING_C_STRUC = 0x100
    ENCODING_JSON   = 0x101

    # configuration: TODO: put this stuff into a configuration file
    _qos = 2
    _topic_base = 'tc/'
    _will_topic =  _topic_base + 'will/'
    _tc_topic_format = _topic_base + '%s/'
    _broker_url = 'mqtt.eug.kerndt.com'  #iot.eclipse.org or test.mosquitto.org
    _broker_port = 1883
    _broker_keepalive = 60
    _bind_address = "100.81.111.18"
    _default_phase_map = { 1:2, 2:3, 3:4, 4:5 } # phase:pin
    _phase_dwell = 0.1
    _debug_level = 3

    # general payload formats
    _payload_type_format = '!i'
    _payload_type_length = struct.calcsize(_payload_type_format)

    # encodings


    def __init__(self):
        #self.lock = threading.Lock()
        self.debug_level = TC._debug_level

    def output_msg(self, msg:str, stream):
        """
        Outputs msg to IOText stream
        :param msg:
        :param stream:
        :return: None
        """
        if isinstance(self, User):
            fmt = "%s %s" % (datetime.now(), msg)
        else:
            fmt = "%s" % (msg,)

        print(fmt, file=stream)
        stream.flush()

    def output_error(self, msg:str):
        """
        Prints message to stderr
        :param msg:str
        :return: None
        """
        self.output_msg(msg, sys.stderr)

    def output_log(self, msg:str):
        """
        Prints message to stdout
        :param msg: str
        :return: None
        """
        self.output_msg(msg, sys.stdout)

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
    def on_will(client, userdata, msg:mqtt.MQTTMessage):
        """
        Called when a will topic is received notifying that a peer has died. Default action is to
        write human readable form to stdout
        :param client: paho.mqtt.client
        :param userdata: TC Server of Client handling callback
        :param mqtt_msg:
        :return: None
        """

        log_msg = None
        try:
            if msg:
                type = TC.get_type(msg.payload)
                if type == TC.WILL:
                    will_id = TC_Identifier.decode(msg)
                    log_msg = "Received will for %s " % (will_id.id,)
                    userdata.output_log(log_msg)
        except TC_Exception:
            log_msg = "Received will of unknown format %s" % (msg.payload,)
            userdata.output_log(log_msg)


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
        rc_string = mqtt.connack_string(rc)
        msg = "Connection response: %s" % (rc_string)
        userdata.output_log(msg)

    @staticmethod
    def on_disconnect(client, userdata, rc):
        """
        Called when the client disconnects from the broker
        :param client: paho.mqtt.client
        :param userdata: TC Server or Client handling callback
        :param flags: dict of broker response flags
        :param rc: int disconnect result
        :return: None
        """
        msg = "Disconnected from broker: %s" % mqtt.error_string(rc)
        userdata.output_log(msg)

    @staticmethod
    def on_message(client, userdata, msg:mqtt.MQTTMessage):
        """
        Called when a message has been received on a topic that the client subscribes to. This callback will be
        called for every message received. Use message_callback_add() to define multiple callbacks that will be
        called for specific topic filters.
        :param client: paho.mqtt.client
        :param userdata: TC Server or Client handling callback
        :param mqtt_msg: MQTTMessage
        :return: None
        """
        if userdata.debug_level > 0:
            msg = "[%s: %s] %s" % (msg.mid, msg.topic, msg.payload)
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
        if userdata.debug_level > 0:
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

        msg = "Subscribe granted on message_id %s with qos %s" % (mqtt_mid, str(granted_qos))
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
        msg = "Unsubscribe acknowledged on message_id %s" % (mqtt_mid,)
        userdata.output_log(msg)


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
        msg = "Log message: level %d - %s" % (level, buf)
        userdata.output_log(msg)

    @staticmethod
    def decode_json(mqtt_msg:mqtt.MQTTMessage):
        """
        Decodes into a dictionary checks whether "type" key is present and then passes onto appropriate TC request class
        for validation and decoding.

        :param payload: JSON dictionary encoding
        :return: TC_type derived class
        """
        payload_string = mqtt_msg.payload.decode("utf-8")
        payload_stream = StringIO(payload_string)
        payload_dict = json.load(payload_stream)
        if "type" in payload_dict:
            type = payload_dict["type"]
            if type == TC.PHASE_REQUEST_ON or type == TC.PHASE_REQUEST_OFF:
                request = TC_Request.json_load(payload_dict)
            elif type == TC.ACK:
                request = TC_ACK.json_load(payload_dict)
            else:
                raise TC_Exception("Unrecognized message type (%d)" % (type,))
            request._encoding = TC.ENCODING_JSON
            request._src_mid = mqtt_msg.mid
            return request


class TC_Type:
    """
    Base TC class which holds only the type value
    """
    _struct_format = '!i'
    _struct_size = struct.calcsize(_struct_format)

    def __init__(self, type:int):
        """
        No reason to create this base type, use decode() to obtain type value from a derived class. But, this
        would be better done using get_type() method in class TC.
        """
        self.type = type
        self._encoding = None
        self._src_mid = None

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
    def decode(cls, msg:mqtt.MQTTMessage):
        """
        Creates a TC_Type object from bytes object which should have been packed using encode() method
        from TC_Type derived object.
        :param msg: MQTTMessage
        :return: TC_Type
        """
        if len(msg.payload) < TC_Type._struct_size:
            msg = 'improperly formatted TC Type (derived) payload'
            raise TC_Exception(msg)
        (type,) = struct.unpack_from(TC_Type._struct_format, msg.payload, 0)
        myType = TC_Type(type)
        myType._encoding = TC.ENCODING_C_STRUC
        myType._src_mid = msg.mid
        return myType

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
    def decode(cls, msg:mqtt.MQTTMessage):
        """
        Creates a TC_Identifier object from bytes object which should have been packed using TC_Identifier.encode()
        or encoded for a derived class.
        :param msg: MQTTMessage
        :return: TC_Identifier object
        """
        if len(msg.payload) < TC_Identifier._struct_size:
            msg = 'improperly formatted TC Will payload'
            raise TC_Exception(msg)
        type, id_bytes = struct.unpack_from(TC_Identifier._struct_format, msg.payload, 0)
        id = id_bytes.decode()
        myID = TC_Identifier(type, id)
        myID._encoding = TC.ENCODING_C_STRUC
        myID._src_mid = msg.mid
        return myID

class TC_Request(TC_Identifier):
    """
    Structure and methods for manipulating mqtt payloads used in traffic control requests
    """

    _struct_format = '!i%ds%dsi' % (TC.MAX_ID_BYTES, TC.MAX_ID_BYTES)
    _struct_size = struct.calcsize(_struct_format)

    def __init__(self, user_id: str, controller_id: str, phase: int):
        """
        Instantiates a Traffic Controller phase request
        :param user_id: str
        :param controller_id: str
        :param phase: int
        """
        super().__init__(TC.PHASE_REQUEST, user_id)
        self.controller_id = controller_id
        self.phase = phase

    def encode(self):
        """
        Converts python values into a bytes object representing a c structure for use in mqtt payload. Strings
        are encoded as a utf-8 bytes object and packed as a char[].

        struct TC_Request {
            int type;
            char user_id[TC.MAX_ID_BYTES];
            char controller_id[TC.MAX_ID_BYTES];
            int phase;
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
        packed = struct.pack(TC_Request._struct_format, self.type, user_id_bytes, controller_id_bytes, self.phase)
        return bytearray(packed)

    @classmethod
    def decode(cls, msg:mqtt.MQTTMessage):
        """
        Creates a TC_Request object from bytes objects which should have been packed using
        TC_Request.encode()

        :param msg: MQTTMessage
        :return: TC_Request
        """
        if len(msg.payload) != TC_Request._struct_size:
            msg = 'improperly formatted TC Request payload: expected %d bytes got %d' % (TC_Request._struct_size, len(msg.payload))
            raise TC_Exception(msg)

        type, user_id_bytes, controller_id_bytes, phase = struct.unpack(TC_Request._struct_format, msg.payload)

        if type != TC.PHASE_REQUEST:
            msg = 'payload claimed to be a phase request but received code (%d)' % type
            raise TC_Exception(msg)
        user_id = user_id_bytes.decode()
        controller_id = controller_id_bytes.decode()

        myRequest = TC_Request(user_id, controller_id, phase)
        myRequest._encoding = TC.ENCODING_C_STRUC
        myRequest._src_mid = msg.mid
        return myRequest

    def json_dump(self, fs):
        """
        Encodes TC_Request object into a JSON string and writes to fs (stream object)
        :param fs:
        :return: None
        """

        # fist stuff object attributes into a dictionary
        json_dict = {}
        json_dict['type'] = self.type
        json_dict['id'] = self.id
        json_dict['controller_id'] = self.controller_id
        json_dict['phase'] =self.phase
        json.dump(json_dict, fs)

    @classmethod
    def json_load(cls, json_dict):
        """
        Creates a TC_ACK Object from a JSON derived dictionary object
        :param json_dict: dict
        :return: TC_ACK
        """

        # validate dictionary and then create TC_Request Object
        if len(json_dict) != TC.TC_ACK_LENGTH:
            msg = "JSON encoding contains %d elements when expecting %d" % (len(json_dict), TC.TC_ACK_LENGTH)
            raise TC_Exception(msg)
        try:
            type = int(json_dict['type'])
            id = json_dict['id']
            controller_id = json_dict['controller_id']
            phase = int(json_dict['phase'])
            new_tc_reqeust = TC_Request(id, controller_id, phase)
            new_tc_reqeust.type = type
            return new_tc_reqeust
        except:
            msg = "Malformed TC_Request Encoding: %s" % (str(json_dict),)
            raise TC_Exception(msg)

    def __str__(self):
        """
        Generates a human readable string suitable for logging
        :return: str
        """
        if self.type == TC.PHASE_REQUEST_ON:
            msg = "User %s requests phase %d on controller %s" % (self.id, self.phase, self.controller_id)
        elif self.type == TC.PHASE_REQUEST_OFF:
            msg = "User %s releases phase %d on controller %s" % (self.id, self.phase, self.controller_id)
        else:
            msg = "User %s sent request type %d to controller %s" % (self.id, self.phase, self.controller_id)
        return msg


class TC_Request_On(TC_Request):
    """
    TC_Request mqtt payload to set phase on
    """

    def __init__(self, user_id: str, controller_id: str, phase: int):
        """

        :param user_id:
        :param controller_id:
        :param phase:
        """
        super().__init__(user_id, controller_id, phase)
        self.type = TC.PHASE_REQUEST_ON

    @classmethod
    def decode(cls, msg:mqtt.MQTTMessage):
        """
        Creates a TC_Request object from bytes objects which should have been packed using
        TC_Request.encode()

        :param msg: MQTTMessage
        :return: TC_Request
        """
        if len(msg.payload) != TC_Request._struct_size:
            msg = 'improperly formatted TC Request payload: expected %d bytes got %d' % (TC_Request._struct_size, len(msg.payload))
            raise TC_Exception(msg)

        type, user_id_bytes, controller_id_bytes, phase = struct.unpack(TC_Request._struct_format, msg.payload)

        if type != TC.PHASE_REQUEST_ON:
            msg = 'payload claimed to be a phase request on but received code (%d)' % type
            raise TC_Exception(msg)
        user_id = user_id_bytes.decode()
        controller_id = controller_id_bytes.decode()

        myRequestOn = TC_Request_On(user_id, controller_id, phase)
        myRequestOn._encoding = TC.ENCODING_C_STRUC
        myRequestOn._src_mid = msg.mid
        return myRequestOn


class TC_Request_Off(TC_Request):
    """
    TC_Request mqtt payload to set phase on
    """

    def __init__(self, user_id: str, controller_id: str, phase: int):
        """

        :param user_id:
        :param controller_id:
        :param phase:
        """
        super().__init__(user_id, controller_id, phase)
        self.type = TC.PHASE_REQUEST_OFF

    @classmethod
    def decode(cls, msg:mqtt.MQTTMessage):
        """
        Creates a TC_Request object from bytes objects which should have been packed using
        TC_Request.encode()

        :param msg: MQTTMessage
        :return: TC_Request
        """
        if len(msg.payload) != TC_Request._struct_size:
            msg = 'improperly formatted TC Request payload: expected %d bytes got %d' % (TC_Request._struct_size, len(msg.payload))
            raise TC_Exception(msg)

        type, user_id_bytes, controller_id_bytes, phase = struct.unpack(TC_Request._struct_format, msg.payload)

        if type != TC.PHASE_REQUEST_OFF:
            msg = 'payload claimed to be a phase request off but received code (%d)' % type
            raise TC_Exception(msg)
        user_id = user_id_bytes.decode()
        controller_id = controller_id_bytes.decode()

        myRequestOff = TC_Request_Off(user_id, controller_id, phase)
        myRequestOff._encoding = TC.ENCODING_C_STRUC
        myRequestOff._src_mid = msg.mid
        return myRequestOff


class TC_ACK(TC_Identifier):
    """
    TC_ACK provides acknowledgement that referenced command suceeded
    """

    # acknowledgement result codes
    OK = 0x00
    INVALID_PHASE = 0x01
    RESULT_CODES = { OK: 'OK',
                     INVALID_PHASE: 'Invalid Phase Number'}

    _struct_format = '!i%dsii' % (TC.MAX_ID_BYTES,)
    _struct_size = struct.calcsize(_struct_format)


    def __init__(self, user_id, mid, result_code):
        """

        :param user_id:
        :param mid:
        :param result_code:
        """
        super().__init__(TC.ACK, user_id)
        self.mid = mid
        self.rc = None
        if result_code in TC_ACK.RESULT_CODES:
            self.rc = result_code
        else:
            raise TC_Exception("Result code %d out of range" % (result_code,))

    def encode(self):
        """
        Converts python values into a bytes object representing a c structure for use in mqtt payload. Strings
        are encoded as a utf-8 bytes object and packed as a char[].

        struct TC_ACK {
            int type;
            char user_id[TC.MAX_ID_BYTES];
            int mid;
            int rc;
            } __attribute__((PACKED));

        :return: bytearray
        """
        user_id_bytes = self.id.encode('utf-8')
        if len(user_id_bytes) > TC.MAX_ID_BYTES:
            msg = "user id <%s> exceeds %d utf-8 bytes" % (self.id, TC.MAX_ID_BYTES)
            raise TC_Exception(msg)
        packed = struct.pack(TC_ACK._struct_format, self.type, user_id_bytes, self.mid, self.rc)
        return bytearray(packed)


    @classmethod
    def decode(cls, msg:mqtt.MQTTMessage):
        """
        Creates a TC_ACK obj from payload that was encoded using TC_ACK.encode
        :param msg: MQTTMessage
        :return:
        """
        if len(msg.payload) != TC_ACK._struct_size:
            msg = 'improperly formatted TC ACK payload: expected %d bytes got %d' % (TC_ACK._struct_size, len(msg.payload))
            raise TC_Exception(msg)

        type, user_id_bytes, mid, rc = struct.unpack(TC_Request._struct_format, msg.payload)

        if type != TC.ACK:
            msg = 'payload claimed to be an ACK but received code (%d)' % type
            raise TC_Exception(msg)
        user_id = user_id_bytes.decode()

        myACK = TC_ACK(user_id, mid, rc)
        myACK._encoding = TC.ENCODING_C_STRUC
        myACK._src_mid = msg.mid

        return myACK


    def json_dump(self, fs):
        """
        Encodes TC_ACK object into a JSON string and writes to fs (stream object)
        :param fs:
        :return: None
        """
        json_dict = {}
        json_dict['type'] = self.type
        json_dict['id'] = self.id
        json_dict['mid'] = self.mid
        json_dict['rc'] =self.rc
        json.dump(json_dict, fs)

    @classmethod
    def json_load(cls, json_dict):
        """
        Creates a TC_ACK Object from a JSON derived dictionary object
        :param json_dict: dict
        :return: TC_ACK
        """
        # validate dictionary and then create TC_Request Object
        if len(json_dict) != TC.TC_ACK_LENGTH:
            msg = "JSON encoding contains %d elements when expecting %d" % (len(json_dict), TC.TC_ACK_LENGTH)
            raise TC_Exception(msg)
        try:
            id = json_dict['id']
            mid = int(json_dict['mid'])
            rc = int(json_dict['rc'])
            return TC_ACK(id, mid, rc)
        except:
            msg = "Malformed TC_Request Encoding: %s" % (str(json_dict),)
            raise TC_Exception(msg)

    def __str__(self):
        """
        Human readable string
        :return: string
        """
        msg = "Acknowledgement of message id %d with result %s" % (self.mid, TC_ACK.RESULT_CODES[self.rc])
        return msg


class TC_phase_request:
    """
    State information we want to keep for a phase loop
    """

    def __init__(self, phase:int, user:str):
        self.phase = phase
        self.timestamp = datetime.now()
        self.user = user


class TC_Relay(threading.Thread):
    """
    Controls relays effecting Traffic Controller Phases. Maintains local phase state and setter methods that ensure
    relayy access methods are executed atomically.
    """

    def __init__(self, parent, pins, max_on_time=TC.MAX_PHASE_ON_SECS):
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
        self._parent = parent
        self._max_delta_time = timedelta(seconds=max_on_time)
        self._valid_pins = frozenset(pins)
        self._phase_queues = dict()
        self._runnable = True
        self._lock = threading.Lock()
        self._update = threading.Event()
        self._timer = threading.Timer(TC.MAX_PHASE_ON_SECS/TC.CHECK_PHASE_TIMEOUT_INTERVAL, self._timeout)

        for pin in pins:
            self._phase_queues[pin] = dict()

    def set_phase_on(self, request:TC_phase_request):
        """
        Sets the state of the pin to on
        :param pin:
        :return: None
        """
        msg = ""
        pin_num = self._parent.phase_to_gpio[request.phase]
        if pin_num in self._valid_pins:
            self._lock.acquire()
            self._timer.cancel()

            phase_queue = self._phase_queues[pin_num]
            if request.user in phase_queue:
                msg = "Extending phase %d (pin %d) time for user %s " % (request.phase, pin_num, request.user)
                self._parent.output_log(msg)
                phase_queue[request.user].timestamp = datetime.now()
            else:
                request.timestamp = datetime.now()
                msg = "Adding user %s to phase %d (pin %d)" % (request.user, request.phase, pin_num)
                self._parent.output_log(msg)
                phase_queue[request.user] = request

            self._timer = threading.Timer(TC.MAX_PHASE_ON_SECS/TC.CHECK_PHASE_TIMEOUT_INTERVAL, self._timeout)
            self._timer.start()
            self._lock.release()
            self._update.set()
        else:
            msg = "Invalid pin %d associated with phase %d request from user %s" % (pin_num, request.phase, request.user)
            self._parent.output_log(msg)


    def set_phase_off(self, request:TC_phase_request):
        """
        Sets the state of pin to off
        :param pin:
        :return: None
        """
        msg = ""
        pin_num = self._parent.phase_to_gpio[request.phase]
        if pin_num in self._valid_pins:
            self._lock.acquire()
            phase_queue = self._phase_queues[pin_num]
            if request.user in phase_queue:
                self._timer.cancel()
                msg = "Removing user %s from phase %d (pin %d) queue" % (request.user, request.phase, pin_num)
                self._parent.output_log(msg)
                del phase_queue[request.user]
                self._timer = threading.Timer(TC.MAX_PHASE_ON_SECS/TC.CHECK_PHASE_TIMEOUT_INTERVAL, self._timeout)
                self._timer.start()
            else:
                msg = "User %s not in queue for phase %d (pin %d)" % (request.user, request.phase, pin_num)
                self._parent.output_log(msg)
            self._lock.release()
            self._update.set()
        else:
            msg = "Invalid pin %d associated with phase %d release from user %s" % (pin_num, request.phase, request.user)
            self._parent.output_log(msg)

    def stop(self):
        """
        Quits thread
        :return: None
        """
        self._runnable = False
        if self._timer:
            self._timer.cancel()
        self._update.set()


    def run(self):
        """

        :return: None
        """
        self._timer.start()
        while self._runnable:
            self._check_states()
            self._update.wait()

    def _timeout(self):
        """
        Calls _check_states and resets the timer
        :return: None
        """
        self._check_states()
        self._timer = threading.Timer(TC.MAX_PHASE_ON_SECS/TC.CHECK_PHASE_TIMEOUT_INTERVAL, self._timeout)
        self._timer.start()

    def _check_states(self):
        """
        Passes through phase queues making gpio calls to set relay to the corresponding phase
        :return: None
        """
        msg = ""
        self._lock.acquire()
        self._update.clear()
        for pin, phase_queue in self._phase_queues.items():
            for phase_request in list(phase_queue.values()):
                msg = ""
                delta_time = datetime.now() - phase_request.timestamp
                if self._parent.debug_level > 1:
                    remaining_time = self._max_delta_time.total_seconds() - delta_time.total_seconds()
                    msg = "User %s has %d seconds remaining in phase %d" % (phase_request.user, remaining_time, phase_request.phase)
                    self._parent.output_log(msg)
                # turn off if exceed max time
                if delta_time > self._max_delta_time:
                    del phase_queue[phase_request.user]
                    msg = "User %s timeout in phase %d (pin %d)" % (phase_request.user, phase_request.phase, pin)
                    self._parent.output_log(msg)
            # TODO: check against actual gpio pin state rather than just setting
            # TODO: also need to add confirmation that write was successful
            value = 0
            if len(phase_queue) > 0:
                value = 1
            grovepi.digitalWrite(pin, value)
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
        self._relays = TC_Relay(self, list(self.phase_to_gpio.values()))

        # using password until we can get TLS setup with user certificates
        self.mqttc.username_pw_set(self.id, password="BikeIoT")

        # pass reference to self for use in callbacks
        self.mqttc.user_data_set(self)

        # defined required topic callbacks
        self.mqttc.will_set(TC._will_topic, TC_Identifier(TC.WILL, self.id).encode())
        self.mqttc.on_connect = TC.on_connect
        self.mqttc.on_disconnect = TC.on_disconnect
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

        # subscribe to own controller_id topic and will topic to get messages intended for me
        self.mqttc.subscribe([(self.tc_topic, TC._qos), (TC._will_topic, TC._qos)])

        # enter network loop forever, relying on interrupt handler to stop things
        self._relays.start()
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
        if self._relays.isAlive():
            self._relays.stop()
            self._relays.join()

    def request_phase(self, request:TC_Request):
        """
        Process phase request to signal traffic controller
        :param request:TC_Request
        :return: None
        """

        rc = TC_ACK.OK

        if request.phase in self.phases:
            if request.type in [TC.PHASE_REQUEST_ON, TC.PHASE_REQUEST_OFF]:
                msg = "processing request type %d for phase %d from %s" % (request.type, request.phase, request.id)
                self.output_log(msg)
                relay_request = TC_phase_request(request.phase, request.id)
                if request.type == TC.PHASE_REQUEST_ON:
                    self._relays.set_phase_on(relay_request)
                else:
                    self._relays.set_phase_off(relay_request)
            else:
                msg = "received an invalid phase reqeust type %d" % (request.type,)
                self.output_log(msg)
        else:
            msg = "received an invalid phase number %d" % (request.phase,)
            self.output_error(msg)
            rc = TC_ACK.INVALID_PHASE

        # send ack
        self.send_ack(request, rc)

    def send_ack(self, tc_cmd:TC_Identifier, rc:int):
        """

        :param tc_cmd: TC_Identifier
        :param rc:
        :return: None
        """
        ack = TC_ACK(tc_cmd.id, tc_cmd._src_mid, rc)
        topic = "%s%s/" % (TC._topic_base, tc_cmd.id)
        if tc_cmd._encoding == TC.ENCODING_JSON:
            payload = StringIO()
            ack.json_dump(payload)
            self.mqttc.publish(topic, payload.getvalue(), TC.DEFAULT_QOS)
        else:
            self.mqttc.publish(topic, ack.encode(), TC.DEFAULT_QOS)

        if self._debug_level > 2:
            msg = "Sent ACK to %s for message id %d with result %d" % (ack.id, ack.mid, ack.rc)
            self.output_log(msg)

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
                request = TC_Request_On.decode(mqtt_msg)
                userdata.request_phase(request)
            elif request_type == TC.PHASE_REQUEST_OFF:
                request = TC_Request_Off.decode(mqtt_msg)
                userdata.request_phase(request)
            elif request_type == TC.ID:
                tc_cmd = TC_Identifier.decode(mqtt_msg)
                userdata.send_ack(tc_cmd, TC_ACK.OK)
            else:
                # try decoding as a json encoded string
                tc_cmd = Server.decode_json(mqtt_msg)
                if tc_cmd.type == TC.ACK:
                    userdata.send_ack(tc_cmd, TC_ACK.OK)
                else:
                    userdata.request_phase(tc_cmd)
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
        self.my_topic = "%s%s/" % (TC._topic_base, self.id)
        self.mqttc = mqtt.Client(user_id)
        self.qos = TC.DEFAULT_QOS

        # using password until we can get TLS setup with user certificates
        self.mqttc.username_pw_set(self.id, password="BikeIoT")

        # pass reference to self for use in callbacks
        self.mqttc.user_data_set(self)

        # defined required topic callbacks
        self.mqttc.will_set(TC._will_topic, TC_Identifier(TC.WILL, self.id).encode())
        self.mqttc.on_connect = TC.on_connect
        self.mqttc.on_disconnect = TC.on_disconnect
        self.mqttc.on_subscribe = TC.on_subscribe
        self.mqttc.on_message = TC.on_message
        self.mqttc.on_publish = TC.on_publish
        self.mqttc.message_callback_add(TC._will_topic, Server.on_will)
        #self.mqttc.message_callback_add(self.my_topic, self.on_topic)

    def start(self):
        """
        Connects to broker and enters loop_forever. Use stop() call to terminate connection to broker and
        terminate loop.
        :return: None
        """
        self.mqttc.connect(self._broker_url, self._broker_port, self._broker_keepalive)

        # subscribe to will topic to get messages intended for me
        self.mqttc.subscribe(self._will_topic, self._qos)
        self.mqttc.subscribe(self.my_topic, self._qos)


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

    def send_phase_request(self, controller_id:str, phase:int):
        """
        Creates a TC_Request_On object and publishes on the appropriate topic
        :param controller_id: str
        :param phase: int
        :param arrival_time: int
        :return: None
        """
        request = TC_Request_On(self.id, controller_id, phase)
        topic = TC._tc_topic_format % controller_id
        msg = "sending reqeust to %s for phase %d" % (controller_id, phase)
        self.output_log(msg)
        self.mqttc.publish(topic, request.encode(), self.qos)

    def send_json_phase_request(self, controller_id:str, phase:int):
        """
        Creates a TC_Request_On object and publishes on the appropriate topic
        :param controller_id: str
        :param phase: int
        :param arrival_time: int
        :return: None
        """
        request = TC_Request_On(self.id, controller_id, phase)
        topic = TC._tc_topic_format % controller_id
        msg = "sending reqeust to %s for phase %d" % (controller_id, phase)
        self.output_log(msg)
        payload = StringIO()
        request.json_dump(payload)
        print("json encoding = %s" % payload.getvalue())
        self.mqttc.publish(topic, payload.getvalue(), self.qos)

    def send_phase_release(self, controller_id:str, phase:int):
        """
        Creates a TC_Reqeust_Off object and publishes on the appropriate topic
        :param controller_id:
        :param phase:
        :param departure_time:
        :return: None
        """
        request = TC_Request_Off(self.id, controller_id, phase)
        topic = TC._tc_topic_format % controller_id
        msg = "sending reqeust to %s for phase %d" % (controller_id, phase)
        self.output_log(msg)
        self.mqttc.publish(topic, request.encode(), self.qos)

    def send_json_phase_release(self, controller_id:str, phase:int):
        """
        Creates a TC_Reqeust_Off object and publishes on the appropriate topic
        :param controller_id:
        :param phase:
        :param departure_time:
        :return: None
        """
        request = TC_Request_Off(self.id, controller_id, phase)
        topic = TC._tc_topic_format % controller_id
        msg = "sending reqeust to %s for phase %d"  % (controller_id, phase)
        self.output_log(msg)
        payload = StringIO()
        request.json_dump(payload)
        self.mqttc.publish(topic, payload.getvalue(), self.qos)

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






