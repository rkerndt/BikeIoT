#!/usr/bin/python3
"""
Module to initialize cellular eth1 device as preinitialization to dhcpcd
"""

from os import environ
from sys import stderr
from subprocess import Popen, DEVNULL

REASON = 'reason'
ADDR_STR = 'new_ip_address'

if REASON in environ:
    if environ[REASON] == "PREINIT":
        proc = Popen("usb_modeswitch -v 0x1410 -p 0x9020 -u 2", stdout=DEVNULL, stderr=DEVNULL)
        result = proc.wait()
        if (result != 0):
            # retry?
            print("Failed to change cellular mode to eth1", file=stderr)
else:
    print("No REASON in environ, not called by dhcpcd-enter-hook?", file=stderr)

exit(0)

