#
#   Copyright (C) 2010-2011 Stackless Recursion
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2, or (at your option)
#   any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
"""Script for ejabberd's external authentication mode."""


import sys
import struct


def from_ejabberd():
    input_length = sys.stdin.read(2)
    (size,) = struct.unpack('>h', input_length)
    return sys.stdin.read(size).split(':')


def to_ejabberd(bool):
    answer = 0
    if bool:
        answer = 1
    token = struct.pack('>hh', 2, answer)
    sys.stdout.write(token)
    sys.stdout.flush()


def auth(username, server, password):
    return True


def isuser(username, server):
    return True


def setpass(username, server, password):
    return True


def main():
    while True:
        data = from_ejabberd()
        success = False
        if data[0] == "auth":
            success = auth(data[1], data[2], data[3])
        elif data[0] == "isuser":
            success = isuser(data[1], data[2])
        elif data[0] == "setpass":
            success = setpass(data[1], data[2], data[3])
        to_ejabberd(success)
