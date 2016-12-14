"""Program for beacon RPi."""
from multiprocessing import Process, Queue
from Queue import Empty
import subprocess
import time
import os
import re
import signal

from bluepy import btle
import grovepi
import picamera
import serial
import sys

DEBUG = True
CELL = False  # Debugging other functions goes faster w/o cellular
SCAN_BLUETOOTH = False # Whether we scan bluetooth for device addresses
TAKE_PICS = True # Whether we take pictures when loop state is on
LOOP_ON = '01'
LOOP_OFF = '00'
MIN_LOOP_ON_COUNT = 1
MIN_DISK_SPACE = 95
IMG_PATH = '/home/pi/Images/'
HCI_DEVICE = 'hci0'

BROADCAST_PERIOD = 60*60  # At least ~540 to use 1 mb per month
if DEBUG:
    BROADCAST_PERIOD = 5
CAM_PERIOD = 12  # How often to take a picture
if DEBUG:
    CAM_PERIOD = 5
SCAN_LEN = 2  # How long to scan bluetooth at one time

# Initialize start time for periodic events
broadcast_time = time.time()
broadcast_time -= BROADCAST_PERIOD  # Makes particle broadcast immediately
cam_time = time.time()

# Set up grovepi
TEMP_HUM_SENSOR = 6  # Connect to D6
LOOP = 5  # Connect to D5
LED = 3  # Connect to D3
grovepi.pinMode(TEMP_HUM_SENSOR, 'INPUT')
grovepi.pinMode(LOOP, 'INPUT')
grovepi.pinMode(TEMP_HUM_SENSOR, 'OUTPUT')
grove_queue = Queue()

# TODO: scanning bluetooth and cell broadcast are intertwined since the
# bluetooth scans are being broadcast over cell. Seperate this out or
# drop bluetooth scanning.

if SCAN_BLUETOOTH:
    # Setup bluetooth
    devices = []
    sc = btle.Scanner(0)

if CELL:
    # Cell configuration
    cell_device = '/dev/ttyACM0' # this is probably wrong!
    cell_baudrate = 115200
    cell_ser = serial.Serial(cell_device, cell_baudrate)

    # Data to send to cell
    broadcast_data = []
    old_broadcast_data = []
    prefixes = ['devs', 'ld', 'temp', 'hum', 'pics']

if TAKE_PICS:
    # Initialize camera
    cam = picamera.PiCamera()

# Bluetooth proccess thread
broadcast_proc = None

def sig_handler(signum, frame):
  # call cleanup on signal
  cleanup()
  sys.exit(0)

def init_ble():
    # always send a reset first, at times hci0 doesn't show up until after
    # after the reset
    error_msg = "OK"
    rslt = subprocess.call('sudo hciconfig hci0 reset', shell=True)
    if rslt !=0:
      error_msg = "hci reset failed with %d" % rslt
      raise Beacon_Error(error_msg)
    rslt = subprocess.call('sudo hciconfig hci0 up', shell=True)
    if rslt != 0:
      error_msg = "hci up failed with %d" % rslt
      raise Beacon_Error(error_msg)
    rslt = subprocess.call('sudo hciconfig hci0 noscanc', shell=True)
    if rslt != 0:
      error_msg = "hci noscanc failed with %d" % rslt
      raise Beacon_Error(error_msg)

def bt_process():
    """Define bluetooth function that will be run as separate process."""

    init_ble()
    
    # only do something when loop state has changed and have confidence in
    # loop on state
    loop_on_count = 0
    previous_loop_state = None
    current_loop_state = LOOP_OFF
    
    while(True):
        try:
            data = get_data()
        except IOError as e:
            if DEBUG:
                print('IOError occured during get_data() %s' % str(e))
        except:
            message = "unexpected error (get_data): %s" % sys.exc_info()[0]
            raise Beacon_Error(message)
            
        # count the number of consecutive times the loop is found on and
        # only set loop state on if above minimum.
        if data[0] == 1:
            loop_on_count += 1;
            if loop_on_count > MIN_LOOP_ON_COUNT:
                current_loop_state = LOOP_ON
            else:
                #keep queue_data in sync with our view of loop state
                data[0] = 0
        else:
            loop_on_count = 0;
            current_loop_state = LOOP_OFF

        set_queue_data(data)

        if previous_loop_state != current_loop_state:
            previous_loop_state = current_loop_state
            try:
                broadcast(data[0])
            except IOError as e:
                if DEBUG:
                    print('IOError occured during ble broadcast: %s' % str(e))
            except:
                message = "Unexpected error (ble broadcast): %s" % sys.exc_info()[0]
                raise Beacon_Error(message)
            try:
                grovepi.digitalWrite(LED, data[0])
            except IOError as e:
                if DEBUG:
                    print('IOError occured during digitalWrite(): %s' % str(e))
            except:
                message = "Unexpected error (digitalWrite): %s" % sys.exc_info()[0]
                raise Beacon_Error(message)


def broadcast(loopstate):
    """Broadcast loopstate over bluetooth."""
    cmdstring = 'sudo hcitool -i hci0 cmd '  # Send cmd to hci0
    cmdstring += '0x08 '  # Set group to BLE
    cmdstring += '0x0008 '  # Set command to HCI_LE_Set_Advertising_Data
    cmdstring += '0D '  # Length of entire following data, in bytes
    cmdstring += '02 '  # Length of flag info
    cmdstring += '01 '  # Use AD flags
    cmdstring += '02 '  # Flag value:
    # bit 0 (OFF) LE Limited Discoverable Mode
    # bit 1 (ON) LE General Discoverable Mode
    # bit 2 (OFF) BR/EDR Not Supported
    # bit 3 (ON) Simultaneous LE and BR/EDR to Same Device Capable (controller)
    # bit 4 (ON) Simultaneous LE and BR/EDR to Same Device Capable (Host)
    cmdstring += '09 '  # Length of following message, in bytes
    cmdstring += '07 '  # GAP value (07 = 128 Bit Complete Service UUID List)
    cmdstring += '42 69 63 79 63 6c 65 '  # Header to identify beacon message-
    # - and it's also is Bicycle in ASCII!
    if loopstate:
            cmdstring = cmdstring + LOOP_ON + ' &>/dev/null'
    else:
        cmdstring = cmdstring + LOOP_OFF + ' &>/dev/null'
    subprocess.call(cmdstring, shell=True)
    subprocess.call('sudo hciconfig hci0 leadv 3 &>/dev/null', shell=True)


def cleanup():
    global broadcast_proc
    """Clean up at program end."""
    if broadcast_proc:
        broadcast_proc.terminate()
        broadcast_proc.join()
    subprocess.call('sudo hciconfig hci0 noleadv', shell=True)
    subprocess.call('sudo hciconfig hci0 reset', shell=True)
    subprocess.call('sudo hciconfig hci0 down', shell=True)
    if CELL:
        ser_command('Cell off', cell_ser)
        cell_ser.close()
    grovepi.digitalWrite(LED, 0)


def get_data():
    """
    Read sensor data right from grovepi.

    Don't call in more than one thread.
    """
    loopstate = None
    temp = None
    hum = None
    loopstate = get_loopstate()
    temp, hum = grovepi.dht(TEMP_HUM_SENSOR, module_type=0)
    return [loopstate, temp, hum]


def get_space():
    """Return what percent of space is left for images."""
    df = subprocess.Popen(['df', IMG_PATH], stdout=subprocess.PIPE)
    output = df.communicate()[0]
    output = output.split('\n')[1]
    output = re.sub(' +', ' ', output)  # Remove repeat spaces
    output = output.split(' ')[4]
    output = int(output[0])
    return output


def get_loopstate():
    """
    Get state of loop, with whatever the system ends up being.

    For now, since it's grovepi, don't call in multiple threads
    """
    return grovepi.digitalRead(LOOP)


def get_queue_data():
    """
    Get loopstate from queue using non-blocking get.
    Safe for all theads. Returns None if get times out.
    """
    data = None
    try:
        data = grove_queue.get(True, 1)
    except Empty:
        pass
    return data


def ser_command(str, ser, responses=['OK\r\n']):
    """Send command over serial, then returns its response."""
    ser.write(str)
    msg = ''
    while (msg not in responses):
        try:
            msg = ser.readline()
        except (OSError, serial.SerialException):
            if DEBUG:
              pass
                #print('Unable to read. Is something else using the port?')
    return msg


def set_queue_data(data):
    """Set data in queue using blocking put. If queue is full
       the  data is lost.
    """
    try:
        grove_queue.put(data)
    except Full as e:
        if DEBUG:
            print('Dropped data %s due to queue full (%d entries)' % (str(data), len(grove_queue)))

def take_img(folder_path):
    """Take picture."""
    title = folder_path + time.ctime() + '.jpg'
    title = title.replace(' ', '_')
    title = title.replace(':', '-')
    cam.capture(title)

class Beacon_Error(Exception):
    """
    A class for all that can go wrong with BLE beacons
    """
    def __init__(self, message):
        self.string = message

    def __str__(self):
        return self.string

    def __repr__(self):
        return("Beacon_Error('%s')" % self.string)


def main():
    global broadcast_proc, cam_time, devices

    # handle sigterm and sigint to exit gracefully
    signal.signal(signal.SIGTERM, sig_handler)
    signal.signal(signal.SIGINT, sig_handler)
 
    # Setup code for before running loop
    broadcast_proc = Process(target=bt_process)

    # Turn on cellular
    if CELL:
        ser_command('Cell on', cell_ser)

   # Main loop
    while(True):
        try:
            # Start bluetooth broadcast in parallel
            if not broadcast_proc.is_alive():
                if DEBUG:
                    print('Starting new bluetooth process')
                del(broadcast_proc)
                broadcast_proc = Process(target=bt_process)
                broadcast_proc.start()

            # Get sensor data
            data = None
            while not data:
                data = get_queue_data()
                
            if DEBUG:
              pass
                # TODO: Broken Print sensor data
                #print('\n** Sensor data **')
                #print('\tTemperature: ' + str(data[1]))
                #print('\tHumidity: ' + str(data[2]))
                #print('\t*****************\n')

            # Take picture only when loop detected at CAM_PERIOD interval
            if TAKE_PICS and (data[0] == 1) and (time.time() - cam_time > CAM_PERIOD):
                cam_time = time.time()
                if DEBUG:
                        print('Space left: %d%%' % get_space())
                if get_space() > MIN_DISK_SPACE:
                    take_img(IMG_PATH)
                # Get number of images taken
                pics = len(os.listdir(IMG_PATH))
                if DEBUG:
                    print('Pics: %d' % pics)

            if SCAN_BLUETOOTH:
                # Check for new devices
                scan_devices = sc.scan(SCAN_LEN)
                for s_dev in scan_devices:
                    for dev in devices:
                        if dev.addr == s_dev.addr:
                            break
                    else:
                        devices.append(s_dev)
                if DEBUG:
                    # Print device count
                    print('Devices found since: %s' % broadcast_time)

                broadcast_data = data[1:4]
                broadcast_data.insert(0, len(devices))
                broadcast_data.insert(len(broadcast_data) - 1, pics)

            # Cell broadcast
            if CELL:
                if (len(old_broadcast_data) != 0) and ((
                    time.time() - broadcast_time) > BROADCAST_PERIOD):
                    if CELL:
                        # Create message to broadcast
                        cell_msg = '{'
                        for i, d in enumerate(broadcast_data):
                            cell_msg += '"' + prefixes[i] + '":' + str(d) + ','
                        cell_msg = cell_msg[:len(cell_msg) - 1] + '}'
                        if DEBUG:
                            print('Old data: %s' % old_broadcast_data)
                            print('New data: %s' % broadcast_data)
                            print('Cell message: ' + cell_msg + '\n')
                        # Send broadcast
                        ser_command(cell_msg, cell_ser)
                        broadcast_time = time.time()
                    # Wipe bluetooth devices after sending cell message
                    devices = []
                old_broadcast_data = broadcast_data

                if DEBUG:
                    print('Cycled')
        except:
            cleanup()
            raise

if __name__ == '__main__':
  main()
  
