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

"""Specify the modules for which a stub exists."""

__all__ = [

    'ftplib',
    'httplib',
    'logging',
    'neo_cgi',
    'py_imp',
    'select',
    'socket',
    'subprocess',
    'tempfile',

    'use_library',
    ]

from cyclozzo.apps.dist import _library

use_library = _library.use_library
