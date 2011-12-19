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
import re
import logging
import logging.handlers
import datetime

import cloghandler

log = logging.getLogger(__name__)

def enable_log(output_path, debug = True, 
            format = '%(asctime)s,%(msecs)03d %(levelname)-5.5s [%(name)s] %(message)s', 
            dateformat = '%H:%M:%S',
            rotating = True, 
            size = 1024 * 1024, 
            copies = 5):
    root = logging.getLogger()
    if debug:
        root.setLevel(logging.DEBUG)
    else:
        root.setLevel(logging.INFO)
        
    formatter = logging.Formatter(format, dateformat)
    
    if rotating:
        handler = cloghandler.ConcurrentRotatingFileHandler(
                        output_path, maxBytes=size, backupCount=copies)
    else:
        handler = logging.handlers.FileHandler(output_path)
    handler.setFormatter(formatter)
    
    root.addHandler(handler)
    root.info('logging facility to "%s"' % output_path)
    root.debug('logger options: debug=%s size=%d copies=%d rotating=%s' % \
            (debug, size, copies, rotating) )