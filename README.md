# bike-project
Setup
=====
Beacon
------
- Uses **Beacon.sh** and **Beacon.py** files
- Install [bluepy](https://github.com/IanHarvey/bluepy), [pyserial](https://github.com/pyserial/pyserial), and [grovepi](https://github.com/DexterInd/GrovePi) (use will **Scripts/install.sh**).
- Create cronjob using `sudo crontab -e` (change `FILE_PATH` to path of Beacon.sh):
```
shell=bin/bash
@reboot sh FILE_PATH >/home/pi/cronlog 2>&1
```
- Enable camera through `raspi-config`
- Disable getty on serial: `sudo systemctl disable serial-getty@ttyAMA0.service`

Receiver
--------
- Uses **Receiver.py** file
- Install [bluepy](https://github.com/IanHarvey/bluepy)
- Create cronjob using `sudo crontab -e` (change `FILE_PATH` to path of Receiver.py):
```
shell=bin/bash
@reboot python FILE_PATH >/home/pi/cronlog 2>&1
```
mDot and Gateway
----------------
- Enable LoRa on Gateway through admin page (available at the IP address of the gateway). Go to *Setup* > *LoRa network server* and check *Enabled*
- Set up serial communication to mDot (baudrate = 115200) and send command `AT`. You should get back `OK`.
- Put both in public mode
  - mDot: Issue `AT+PN=1`
  - Gateway: Check *Public*
- Make sure they have the same Network ID, Network key, and Frequency Sub-Band
  - Gateway: Change in LoRa menu
  - mDot: Set `AT+NK`, `AT+NI`, and `AT+FSB` to the correct values  
- Check if the mDot's address is within the gateway's address range. If not, set it with `AT+NA`.
- Once all settings are correct, use `AT&W` to save them.

Additionally, the gateway will need the Node-RED flow imported. In Node-RED (*Apps* > *Node-RED*) go to *Import* > *Clipboard* and paste in **flow.JSON**.
