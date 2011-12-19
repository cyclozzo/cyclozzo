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

"""Errors used in the Python appinfo API, used by app developers."""





class Error(Exception):
  """Base datastore AppInfo type."""

class EmptyConfigurationFile(Error):
  """Tried to load empty configuration file"""

class MultipleConfigurationFile(Error):
  """Tried to load configuration file with multiple AppInfo objects"""

class UnknownHandlerType(Error):
  """Raised when it is not possible to determine URL mapping type."""

class UnexpectedHandlerAttribute(Error):
  """Raised when a handler type has an attribute that it does not use."""

class MissingHandlerAttribute(Error):
  """Raised when a handler is missing an attribute required by its type."""

class MissingURLMapping(Error):
  """Raised when there are no URL mappings in external appinfo."""

class TooManyURLMappings(Error):
  """Raised when there are too many URL mappings in external appinfo."""

class PositionUsedInAppYamlHandler(Error):
  """Raised when position attribute is used in handler in AppInfoExternal."""

class InvalidBuiltinFormat(Error):
  """Raised when the name of the builtin in a list item cannot be identified."""

class MultipleBuiltinsSpecified(Error):
  """Raised when more than one builtin is specified in a single list element."""

class DuplicateBuiltinsSpecified(Error):
  """Raised when a builtin is specified more than once in the same file."""
