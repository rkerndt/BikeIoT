#!/usr/bin/python3
"""
Functions to simplify TC_server testing and demostration
"""

import TC_server

myUserID = input("Please enter a user id: ")
controllerID = 'beacon_1.cs.uoregon.edu'

myUser = TC_server.User(myUserID)
myUser.debug_level = 0
myUser.start()


while True:
    try:
        command_line = input("\nBikeIoT > ")
        command_line = command_line.strip()
        commands = command_line.split()
        good = True
        if len(commands) == 0:
            continue
        if len(commands) == 3:
            op, phase, arrival = commands
        else:
            good = False
        if good and phase.isdigit():
            phase = int(phase)
        else:
            good = False
        if good and arrival.isdigit():
            arrival = int(arrival)
        else:
            good = False
        if good:
            if op == 'on':
                myUser.send_json_phase_request(controllerID, phase, arrival)
            elif op == 'off':
                myUser.send_json_phase_release(controllerID, phase, arrival)
            else:
                good = False
        if not good:
            print("USAGE: [on | off] phase seconds")
    except KeyboardInterrupt:
        myUser.stop()
        print()
        exit(0)
