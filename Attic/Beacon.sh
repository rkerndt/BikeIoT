#!/bin/bash
sudo hciconfig hci0 up
sudo hciconfig hci0 noscanc
sudo python /home/pi/Beacon.py &>>/home/pi/beacon.log
