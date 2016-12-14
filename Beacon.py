"""Program for beacon RPi."""
from __future__ import print_funtion
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
import sys.stderr

DEBUG = True
CELL = False  # Debugging other functions goes faster w/o cellular
SCAN_BLUETOOTH = False # Whether we scan bluetooth for device addresses
TAKE_PICS = True # Whether we take pictures when loop state is on
LOOP_ON = '01'
LOOP_OFF = '00'
MIN_DISK_SPACE = 95
IMG_PATH = '/home/pi/Images/'
HCI_DEVICE = hci0
OUT_FILE = stderr

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
LOUDNESS_SENSOR = 0  # Connect to A0
TEMP_HUM_SENSOR = 6  # Connect to D6
LOOP = 5  # Connect to D5
LED = 3  # Connect to D3
grovepi.pinMode(LOUDNESS_SENSOR, 'INPUT')
grovepi.pinMode(TEMP_HUM_SENSOR, 'INPUT')
grovepi.pinMode(LOOP, 'INPUT')
grovepi.pinMode(TEMP_HUM_SENSOR, 'OUTPUT')
grove_queue = Queue()
grove_data = []

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

def init_ble():
    # always send a reset first, at times hci0 doesn't show up until after
    # after the reset
    error_msg = "OK"
    rslt = subprocess.call('sudo hcitool hci0 reset', shell=True)
    if rslt !=0:
      error_msg = "hci reset failed with %d" % rslt
    else:
      rslt = subprocess.call('sudo hciconfig hci0 up', shell=True)
    if rslt != 0:
      error_msg = "hci up failed with %d" % rslt
    else:
      rslt = subprocess.call('sudo hciconfig hci0 noscan', shell=True)
    if rslt != 0:
      error_msg = "hci noscan failed with %d" % rslt
    if rslt != 0:
      raise Beacon_Error(error_msg)

def bt_process():
    """Define bluetooth function that will be run as separate process."""

    # only do something when loop state has changed
    previous = None
    try:
        while(True):
            data = get_data()
            set_queue_data(data)
            if previous != data[0]:
                previous = data[0]
                broadcast(data[0])
                grovepi.digitalWrite(LED, data[0])
    except IOError:
        if DEBUG:
            print('IOError detected and excepted: %s' % str(IOError),file=OUT_FILE)
        pass
    except:
      message = "Unexpected error: %s" % sys.exc_into()[0]
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
    broadcast_proc.terminate()
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
    loopstate = get_loopstate()
    loudness = grovepi.analogRead(LOUDNESS_SENSOR)
    [temp, hum] = grovepi.dht(TEMP_HUM_SENSOR, module_type=0)
    return [loopstate, loudness, temp, hum]


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
    Get loopstate from queue.

    Safe for all theads.
    """
    global grove_data
    try:
        grove_data = grove_queue.get_nowait()
    except Empty:
        # Just use old loopstate if queue is empty
        pass
    return grove_data


def ser_command(str, ser, responses=['OK\r\n']):
    """Send command over serial, then returns its response."""
    ser.write(str)
    msg = ''
    while (msg not in responses):
        try:
            msg = ser.readline()
        except OSError, serial.SerialException:
            if DEBUG:
                print('Unable to read. Is something else using the port?',file=OUT_FILE)
    return msg


def set_queue_data(data):
    """Set data in queue."""
    while(not grove_queue.empty):
        grove_queue.get()
    grove_queue.put(data)


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
 
    # Initialize ble
    init_ble()

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
                    print('Starting new bluetooth process',file=OUT_FILE)
                del(broadcast_proc)
                broadcast_proc = Process(target=bt_process)
                broadcast_proc.start()

            # Get sensor data
            data = []
            while len(data) == 0:
                data = get_queue_data()
                
            if DEBUG:
                # Print sensor data
                print('\n** Sensor data **',file=OUT_FILE)
                print('\tLoudness: ' + str(data[1]),file=OUT_FILE)
                print('\tTemperature: ' + str(data[2]),file=OUT_FILE)
                print(\t'Humidity: ' + str(data[3]),file=OUT_FILE)
                print(\t'*****************\n',file=OUT_FILE)

            # Take picture only when loop detected at CAM_PERIOD interval
            if TAKE_PICS and data[0] and (time.time() - cam_time > CAM_PERIOD):
                cam_time = time.time()
                if DEBUG:
                        print('Space left: %d%%' % get_space(),file=OUT_FILE)
                if get_space() < MIN_DISK_SPACE:
                    take_img(IMG_PATH)
                # Get number of images taken
                pics = len(os.listdir(IMG_PATH))
                if DEBUG:
                  print('Pics: %d' % pics,file=OUT_FILE)

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
                    print('Devices found since ',file=OUT_FILE,end="")
                    print(broadcast_time,file=OUT_FILE)

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
                            print('Old data: %s' % old_broadcast_data,file=OUT_FILE)
                            print('New data: %s' % broadcast_data,file=OUT_FILE)
                            print('Cell message: ' + cell_msg + '\n',file=OUT_FILE)
                        # Send broadcast
                        ser_command(cell_msg, cell_ser)
                        broadcast_time = time.time()
                    # Wipe bluetooth devices after sending cell message
                    devices = []
                old_broadcast_data = broadcast_data

                if DEBUG:
                    print('Cycled',file=OUT_FILE)
        except:
            cleanup()
            raise

if __name__ == '__main__':
  main()
  
