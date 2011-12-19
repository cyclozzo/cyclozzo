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
"""The Python datastore protocol buffer definition.

Proto2 compiler expects generated file names to follow specific pattern,
which is not the case for the datastore_pb.py (should be datastore_v3_pb.py).
This file with the expected name redirects to the real legacy file.
"""


from cyclozzo.apps.datastore.datastore_pb import *
