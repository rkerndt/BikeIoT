"""Program for receiver RPi."""

from bluepy import btle
import RPi.GPIO as GPIO
import sys
import signal
import datetime

# add pi python module dir to sys.path
sys.path.append("/home/pi/lib/python")
import rgb


class Bike_loop:
    """
    Acts as receiver for Bluetooth LE Traffic Signal Loop Detection
    """

    LOOP_ON = '01'
    LOOP_OFF = '00'
    PROCESS_TIMEOUT = 0.1 # seconds
    BEACON_TIMEOUT  = datetime.timedelta(milliseconds=300) # seconds
    BEACON_ITEM = 7
    BEACON_KEY = '42696379636c56'
    LED_PINS = (21,20,16)

    def __init__(self, debug=False):
        """

        """
        self._debug = debug
        self._led = None
        self._btle_scanner = None
        self._last_seen = None
        self._beacon_detected = False
        self._loop_state = False

    def start(self):
        """
        Processes Bluetooth LE beacons until SIGINT or SIGTERM received.
        """

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        self._led = rgb.RGB_led(*Bike_loop.LED_PINS)
        self._btle_scanner = btle.Scanner(0).withDelegate(self.handleDiscovery)
        self._btle_scanner.clear()
        self._btle_scanner.start()
        self._led.green(True)

        while True:
            self._btle_scanner.process(Bike_loop.PROCESS_TIMEOUT)
            if self._beacon_detected:
                self._check_beacon_timeout()

    def handleDiscovery(self, scan_entry, isNew, isNewData):
        """
        Callback from scanner to process scan entries
        :param scan_entry:
        :param isNew:
        :param isNewData:
        """
        beacon_detected = False
        loop_state = False

        if self._debug:
            print('address = %s' % scan_entry.addr)
            for adtype, description, value in scan_entry.getScanData():
                print('\t%s, %s, %s' % (adtype, description, value))
            print()

        msg = scan_entry.getValueText(Bike_loop.BEACON_ITEM)
        if (msg is not None) and (msg[:len(msg) - 2] == Bike_loop.BEACON_KEY):
            self._last_seen = datetime.datetime.now()
            loop_state = (msg[len(msg) - 2:] == Bike_loop.LOOP_ON)

            # only change led if we need to
            if (not self._beacon_detected) or (loop_state != self._loop_state):
                self._beacon_detected = True
                if loop_state:
                    self._loop_state = True
                    self._led.blue()
                else:
                    self._loop_state = False
                    self._led.red()
        elif self._beacon_detected:
            self._check_beacon_timeout()


    def _check_beacon_timeout(self):
        """
        Sets led to green blinking when beacon has not been seen within its timeout period
        """
        if self._last_seen:
            since_last_seen = datetime.datetime.now() - self._last_seen
            if since_last_seen > Bike_loop.BEACON_TIMEOUT:
                self._beacon_detected = False
                self._loop_state = False
                self._led.green(True)


    def _signal_handler(self, signum, frame):
        """
        Closes down btle_scanner and led objects before exiting
        :param signum:
        :param frame:
        """

        self._led.close()
        self._btle_scanner.stop()
        exit()


def main(args):

    debug = False

    if len(args) >= 2 and args[1] == "debug":
        debug = True

    bike_loop_scan = Bike_loop(debug)
    bike_loop_scan.start()

if __name__ == "__main__":
    main(sys.argv)