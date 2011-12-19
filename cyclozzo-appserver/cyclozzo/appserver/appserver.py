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
import os
import sys
from cyclozzo.apps.tools import os_compat

if not hasattr(sys, 'version_info'):
  sys.stderr.write('Very old versions of Python are not supported. Please '
                   'use version 2.5 or greater.\n')
  sys.exit(1)
version_tuple = tuple(sys.version_info[:2])
if version_tuple < (2, 4):
  sys.stderr.write('Error: Python %d.%d is not supported. Please use '
                   'version 2.5 or greater.\n' % version_tuple)
  sys.exit(1)
if version_tuple == (2, 4):
  sys.stderr.write('Warning: Python 2.4 is not supported; this program may '
                   'break. Please use version 2.5 or greater.\n')

SDK_PATH = os.path.dirname(
						os.path.dirname(
									os.path.dirname(
												os.path.dirname(os_compat.__file__)
												)
									)
						)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

EXTRA_PATHS = [
  SDK_PATH,
  os.path.join(SDK_PATH, 'cyclozzo', 'lib', 'antlr3'),
  os.path.join(SDK_PATH, 'cyclozzo', 'lib', 'django'),
  os.path.join(SDK_PATH, 'cyclozzo', 'lib', 'fancy_urllib'),
  os.path.join(SDK_PATH, 'cyclozzo', 'lib', 'ipaddr'),
  os.path.join(SDK_PATH, 'cyclozzo', 'lib', 'webob'),
  os.path.join(SDK_PATH, 'cyclozzo', 'lib', 'yaml', 'lib'),
  os.path.join(SDK_PATH, 'cyclozzo', 'lib', 'tornado'),
]

SCRIPT_EXCEPTIONS = {
  "appserver.py" : "server.py"
}


def fix_sys_path():
  """Fix the sys.path to include our extra paths."""
  sys.path = EXTRA_PATHS + sys.path


def run_file(file_path, globals_, script_dir=SCRIPT_DIR):
  """Execute the file at the specified path with the passed-in globals."""
  fix_sys_path()
  script_name = os.path.basename(file_path)
  script_name = SCRIPT_EXCEPTIONS.get(script_name, script_name)
  script_path = os.path.join(script_dir, script_name)
  print script_path
  execfile(script_path, globals_)


if __name__ == '__main__':
  run_file(__file__, globals())
