#!/usr/bin/env python
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


__all__ = [
    "lock",
    "unlock",
    "LOCK_EX",
    "LOCK_SH",
    "LOCK_NB",
    "LockException",
]

import os
from types import IntType

class LockException(Exception):
    # Error codes:
    LOCK_FAILED = 1

if os.name == 'nt':
    import win32con
    import win32file
    import pywintypes
    LOCK_EX = win32con.LOCKFILE_EXCLUSIVE_LOCK
    LOCK_SH = 0 # the default
    LOCK_NB = win32con.LOCKFILE_FAIL_IMMEDIATELY
    # is there any reason not to reuse the following structure?
    __overlapped = pywintypes.OVERLAPPED()
elif os.name == 'posix':
    import fcntl
    LOCK_EX = fcntl.LOCK_EX
    LOCK_SH = fcntl.LOCK_SH
    LOCK_NB = fcntl.LOCK_NB
else:
    raise RuntimeError, "PortaLocker only defined for nt and posix platforms"



def _getfd(file):
    """ Get a file-descriptor from a file object or file-descriptor. """
    if hasattr(file, "fileno"):
        return file.fileno()
    elif type(file) == IntType:
        return file
    else:
        raise TypeError("File object or file descriptor required, but %s "
                        "was provided." % type(file))


if os.name == 'nt':
    def lock(file, flags):
        hfile = win32file._get_osfhandle(_getfd(file))
        try:
            win32file.LockFileEx(hfile, flags, 0, -0x10000, __overlapped)
        except pywintypes.error, exc_value:
            # error: (33, 'LockFileEx', 'The process cannot access the file because another process has locked a portion of the file.')
            if exc_value[0] == 33:
                raise LockException(LockException.LOCK_FAILED, exc_value[2])
            else:
                # Q:  Are there exceptions/codes we should be dealing with here?
                raise
    
    def unlock(file):
        hfile = win32file._get_osfhandle(_getfd(file))
        try:
            win32file.UnlockFileEx(hfile, 0, -0x10000, __overlapped)
        except pywintypes.error, exc_value:
            if exc_value[0] == 158:
                # error: (158, 'UnlockFileEx', 'The segment is already unlocked.')
                # To match the 'posix' implementation, silently ignore this error
                pass
            else:
                # Q:  Are there exceptions/codes we should be dealing with here?
                raise

elif os.name == 'posix':
    def lock(file, flags):
        try:
            fcntl.flock(_getfd(file), flags)
        except IOError, exc_value:
            #  IOError: [Errno 11] Resource temporarily unavailable
            if exc_value[0] == 11:
                raise LockException(LockException.LOCK_FAILED, exc_value[1])
            else:
                raise
    
    def unlock(file):
        fcntl.flock(_getfd(file), fcntl.LOCK_UN)



if __name__ == '__main__':
    from time import time, strftime, localtime
    import sys
    import portalocker

    log = open('log.txt', "a+")
    portalocker.lock(log, portalocker.LOCK_EX)

    timestamp = strftime("%m/%d/%Y %H:%M:%S\n", localtime(time()))
    log.write( timestamp )

    print "Wrote lines. Hit enter to release lock."
    dummy = sys.stdin.readline()

    log.close()

