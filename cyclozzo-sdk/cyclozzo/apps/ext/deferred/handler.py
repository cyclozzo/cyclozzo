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

"""Request handler module for the deferred library.

See deferred.py for full documentation.
"""





from cyclozzo.apps.ext import deferred
from cyclozzo.apps.ext.webapp.util import run_wsgi_app


def main():
  run_wsgi_app(deferred.application)


if __name__ == "__main__":
  main()
