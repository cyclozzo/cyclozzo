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

"""Repository for all builtin handlers information.

On initialization, this file generates a list of builtin handlers that have
associated app.yaml information.  This file can then be called to read that
information and make it available.
"""




import logging
import os

DEFAULT_DIR = os.path.join(os.path.dirname(__file__))
HANDLER_DIR = None

AVAILABLE_BUILTINS = None

INCLUDE_FILENAME = 'include.yaml'


class InvalidBuiltinName(Exception):
  """Raised whenever a builtin handler name is specified that is not found."""


def reset_builtins_dir():
  """Public method for resetting builtins directory to default."""
  set_builtins_dir(DEFAULT_DIR)


def set_builtins_dir(path):
  """Sets the appropriate path for testing and reinitializes the module."""
  global HANDLER_DIR, AVAILABLE_BUILTINS
  HANDLER_DIR = path
  AVAILABLE_BUILTINS = []
  _initialize_builtins()


def _initialize_builtins():
  """Scan the immediate subdirectories of the builtins module.

  Encountered subdirectories with an app.yaml file are added to
  AVAILABLE_BUILTINS.
  """
  for filename in os.listdir(HANDLER_DIR):
    if os.path.isfile(_get_yaml_path(filename)):
      AVAILABLE_BUILTINS.append(filename)


def _get_yaml_path(builtin_name):
  """Return expected path to a builtin handler's yaml file without error check.
  """
  return os.path.join(HANDLER_DIR, builtin_name, INCLUDE_FILENAME)


def get_yaml_path(builtin_name):
  """Returns the full path to a yaml file by giving the builtin module's name.

  Args:
    builtin_name: single word name of builtin handler

  Raises:
    ValueError: if handler does not exist in expected directory

  Returns:
    the absolute path to a valid builtin handler include.yaml file
  """
  if builtin_name not in AVAILABLE_BUILTINS:
    raise InvalidBuiltinName('%s is not the name of a valid builtin handler.\n'
                             'Available handlers are: %s' % (
                             builtin_name, ', '.join(AVAILABLE_BUILTINS)))
  return _get_yaml_path(builtin_name)


set_builtins_dir(DEFAULT_DIR)
