#!/usr/bin/python3
"""
Functions to simplify TC_server testing and demostration
"""

import TC_server
from datetime import datetime, timedelta

myUserID = input("Please enter a user id: ")
myBroker = input("Please enter broker url: ")
controllerID = 'beacon_1.cs.uoregon.edu'

myUser = TC_server.User(myUserID)
myUser.debug_level = 0
myUser._broker_url =  myBroker
myUser.start()


while True:
    try:
        command_line = input("\nBikeIoT > ")
        command_line = command_line.strip()
        commands = command_line.split()
        good = True
        if len(commands) == 0:
            continue
        if commands[0] == 'on' and commands[1].isdigit():
            myUser.send_phase_request(controllerID, int(commands[1]))
        elif commands[0] == 'off' and commands[1].isdigit():
            myUser.send_phase_release(controllerID, int(commands[1]))
        elif commands[0] == 'ping':
            num = 1
            count = 0
            sum = 0
            if len(commands)== 2 and commands[1].isdigit():
                num = int(commands[1])
            while count < num:
                start = datetime.now()
                myUser.ping(controllerID)
                myUser._ack_event.clear()
                myUser._ack_event.wait()
                delta = datetime.now() - start
                print("%d on %s in %f seconds" % (count, controllerID, delta.total_seconds()), flush=True)
                sum += delta.total_seconds()
                count += 1
            if count > 1:
                print("Averge RTT = %f seconds" % (sum/count,))
        else:
            print("USAGE: [on | off] phase")
    except KeyboardInterrupt:
        myUser.stop()
        print()
        exit(0)
    except Exception as e:
        print(e)
        pass
