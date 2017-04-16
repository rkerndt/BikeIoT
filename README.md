# IoT Bike System
Use this software to set up an IoT bike system with raspberry pis. The beacon raspberry pi, which taps into a bike traffic light, broadcasts to the receiver pi over bluetooth whether or not the traffic light has detected the bike. The beacon also sends information and sensor data back to a base station over cellular and LoRa.

Hardware used
------------

**Beacon**:
- Raspberry Pi 3
- GrovePi
- Grove Temperature and Humidity Sensor Pro
- Rasberry Pi Camera Board, Rev 1.3
- Power supply, Mean Well RS-15-5 (5VDC, 3AMP)
- Grove - Relay (4)
- Box
- Pushbutton, Momentary, Normally Closed, Schneider Electric (PN 9001KR1BH6)
- Panels, acryllic sheet 0.220in (5.6mm) thickness
- Wire, 22ga (black & red), 18ga (black)
- Cell Mode, MiFi 4G LTE Global USB Modem (U620L)
- Heyco 3213 liquid tight fitting
- Mounting hardware, M2 & M3 4mm standoff with screws

**Raspberry Pi Configuration**
-----
Install raspberry pi with latest version of raspbian-jessie-lite os.

Connect the pi to a usb keyboard and monitor, boot and login to the pi account (username: pi, password: raspberry)

With the raspi-config configuration application:
  1. enable serial console
  2. enable remote ssh login

Add the following lines to /boot/config.txt. These statements will disable the built-in bluetooth and fix the core frequency. The purpose of this is to allow use of tty0 as the serial console and provide a stable baud rate timing.
```
  # Enable serial console
  dtoverlay=pi3-miniuart-bt
  enable_uart=1
```
Check that the file /boot/cmdline.txt contains the following settings:
  ```
  console=serial0,115200 console=tty1
  ```
  
The TC_server.py code requires I2C enabled. Check that the following is set in /boot/config.txt.
```
  dtparam=i2c_arm=on
```
Additional packages required by TC_server.py
  - python3
  - i2c-tools
  - libi2c-dev
  - python-smbus
  - paho-mqtt
  
Set up user accounts using passwd and the adduser shell command
  1. First create an admin account:
    ```
    adduser -ingroup sudo admin
    ```
  2. Verify that you can log into the admin account, then ...
  3. Disable login for user pi from the admin account:
    ```
    sudo passwd -i pi
    ```
  
From the admin's home directory clone the git BikeIoT repository:
```
  git clone https://git.com/rkerndt/BikeIoT
```

Copy the following service files to /etc/systemd/system.
  - tc_service.service
  - cellular-init.service
  - serial-getty@.service
  
Enable services using the command:
```
  sudo systemctl enable <name>
```
  
Copy TC_server.py, grovepi.py, and TC.config to /home/pi.

Customize settings in TC.config for this beacon box.

The tc_service can now be starting by rebooting or in the following order:
```
  sudo systemctl daemon-reload
  sudo systemctl start cellular-init.service
  sudo systemctl start tc_service.service
```
  
