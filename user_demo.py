#!/usr/bin/python3
"""
Functions to simplify TC_server testing and demostration
"""

import TC_server as TC
from datetime import datetime, timedelta

USAGE = "controller <controller_id>\n"
USAGE += "ON | OFF <phase>\n"
USAGE += "ping <num>\n"
USAGE += "reboot\n"
USAGE += "wifi enable | disable\n"
USAGE += '\n'

myUserID = input("Please enter a user id: ")
myBroker = input("Please enter broker url: ")
controllerID = 'beacon_1.cs.uoregon.edu'

myUser = TC.User(myUserID)
myUser.debug_level = 0
myUser._broker_url =  myBroker
myUser.start()


while True:
    try:
        command_line = input("\nBikeIoT [%s]: " % (controllerID,))
        command_line = command_line.strip()
        commands = command_line.split()
        myUser._wait_for_ack = True
        myUser._ack_event.clear()
        if len(commands) == 0:
            continue
        if commands[0] == 'controller' and len(commands) == 2:
            controllerID = commands[1]
        elif commands[0] == 'on' and len(commands) == 2 and commands[1].isdigit():
            myUser.send_phase_request(controllerID, int(commands[1]))
        elif commands[0] == 'off' and len(commands) == 2 and commands[1].isdigit():
            myUser.send_phase_release(controllerID, int(commands[1]))
        elif commands[0] == 'ping':
            myUser._wait_for_ack = False
            num = 1
            count = 0
            sum_count = 0
            sum = 0
            if len(commands)== 2 and commands[1].isdigit():
                num = int(commands[1])
            while count < num:
                start = datetime.now()
                myUser.ping(controllerID)
                myUser._ack_event.clear()
                if myUser._ack_event.wait(timeout=10):
                    delta = datetime.now() - start
                    print("%d on %s in %f seconds" % (count, controllerID, delta.total_seconds()), flush=True)
                    sum += delta.total_seconds()
                    sum_count += 1
                else:
                    print("%d on %s timeout" % (count, controllerID))
                count += 1
            if count > 1:
                print("Averge RTT of %d returned = %f seconds" % (sum_count, sum/sum_count))
        elif commands[0] == 'reboot' and len(commands) == 2:
            tc_cmd = TC.TC_Admin(TC.TC.ADMIN_REBOOT, myUserID, commands[1])
            myUser.mqttc.publish(TC.TC._tc_admin_format % commands[1], tc_cmd.encode(), TC.TC._qos)
        elif commands[0] == 'wifi' and len(commands) == 2 and commands[1] == 'enable':
            tc_cmd = TC.TC_Admin(TC.TC.ADMIN_WIFI_ENABLE, myUserID, controllerID)
            myUser.mqttc.publish(TC.TC._tc_admin_format % controllerID, tc_cmd.encode(), TC.TC._qos)
        elif commands[0] == 'wifi' and len(commands) == 2 and commands[1] == 'disable':
            tc_cmd = TC.TC_Admin(TC.TC.ADMIN_WIFI_DISABLE, myUserID, controllerID)
            myUser.mqttc.publish(TC.TC._tc_admin_format % controllerID, tc_cmd.encode(), TC.TC._qos)
        else:
            print(USAGE)
            continue
        if myUser._wait_for_ack and not myUser._ack_event.wait(timeout=10):
            print("Command %s timed out" % (commands[0],))

    except KeyboardInterrupt:
        myUser.stop()
        print()
        exit(0)
    except Exception as e:
        print(e)

