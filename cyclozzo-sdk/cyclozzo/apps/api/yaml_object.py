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
"""Builder for mapping YAML documents to object instances.

ObjectBuilder is responsible for mapping a YAML document to classes defined
using the validation mechanism (see cyclozzo.apps.api.validation.py).
"""





from cyclozzo.apps.api import validation
from cyclozzo.apps.api import yaml_listener
from cyclozzo.apps.api import yaml_builder
from cyclozzo.apps.api import yaml_errors

import yaml


class _ObjectMapper(object):
  """Wrapper used for mapping attributes from a yaml file to an object.

  This wrapper is required because objects do not know what property they are
  associated with a creation time, and therefore can not be instantiated
  with the correct class until they are mapped to their parents.
  """

  def __init__(self):
    """Object mapper starts off with empty value."""
    self.value = None
    self.seen = set()

  def set_value(self, value):
    """Set value of instance to map to.

    Args:
      value: Instance that this mapper maps to.
    """
    self.value = value

  def see(self, key):
    if key in self.seen:
      raise yaml_errors.DuplicateAttribute("Duplicate attribute '%s'." % key)
    self.seen.add(key)

class _ObjectSequencer(object):
  """Wrapper used for building sequences from a yaml file to a list.

  This wrapper is required because objects do not know what property they are
  associated with a creation time, and therefore can not be instantiated
  with the correct class until they are mapped to their parents.
  """

  def __init__(self):
    """Object sequencer starts off with empty value."""
    self.value = []
    self.constructor = None

  def set_constructor(self, constructor):
    """Set object used for constructing new sequence instances.

    Args:
      constructor: Callable which can accept no arguments.  Must return
        an instance of the appropriate class for the container.
    """
    self.constructor = constructor


class ObjectBuilder(yaml_builder.Builder):
  """Builder used for constructing validated objects.

  Given a class that implements validation.Validated, it will parse a YAML
  document and attempt to build an instance of the class.  It does so by mapping
  YAML keys to Python attributes.  ObjectBuilder will only map YAML fields
  to attributes defined in the Validated subclasses 'ATTRIBUTE' definitions.
  Lists are mapped to validated.  Repeated attributes and maps are mapped to
  validated.Type properties.

  For a YAML map to be compatible with a class, the class must have a
  constructor that can be called with no parameters.  If the provided type
  does not have such a constructor a parse time error will occur.
  """

  def __init__(self, default_class):
    """Initialize validated object builder.

    Args:
      default_class: Class that is instantiated upon the detection of a new
        document.  An instance of this class will act as the document itself.
    """
    self.default_class = default_class

  def _GetRepeated(self, attribute):
    """Get the ultimate type of a repeated validator.

    Looks for an instance of validation.Repeated, returning its constructor.

    Args:
      attribute: Repeated validator attribute to find type for.

    Returns:
      The expected class of of the Type validator, otherwise object.
    """
    if isinstance(attribute, validation.Optional):
      attribute = attribute.validator
    if isinstance(attribute, validation.Repeated):
      return attribute.constructor
    return object

  def BuildDocument(self):
    """Instantiate new root validated object.

    Returns:
      New instance of validated object.
    """
    return self.default_class()

  def BuildMapping(self, top_value):
    """New instance of object mapper for opening map scope.

    Args:
      top_value: Parent of nested object.

    Returns:
      New instance of object mapper.
    """
    result = _ObjectMapper()
    if isinstance(top_value, self.default_class):
      result.value = top_value
    return result

  def EndMapping(self, top_value, mapping):
    """When leaving scope, makes sure new object is initialized.

    This method is mainly for picking up on any missing required attributes.

    Args:
      top_value: Parent of closing mapping object.
      mapping: _ObjectMapper instance that is leaving scope.
    """
    try:
      mapping.value.CheckInitialized()
    except validation.ValidationError:
      raise
    except Exception, e:
      try:
        error_str = str(e)
      except Exception:
        error_str = '<unknown>'

      raise validation.ValidationError("Invalid object:\n%s" % error_str, e)

  def BuildSequence(self, top_value):
    """New instance of object sequence.

    Args:
      top_value: Object that contains the new sequence.

    Returns:
      A new _ObjectSequencer instance.
    """
    return _ObjectSequencer()

  def MapTo(self, subject, key, value):
    """Map key-value pair to an objects attribute.

    Args:
      subject: _ObjectMapper of object that will receive new attribute.
      key: Key of attribute.
      value: Value of new attribute.

    Raises:
      UnexpectedAttribute when the key is not a validated attribute of
      the subject value class.
    """
    assert subject.value is not None
    if key not in subject.value.ATTRIBUTES:
      raise yaml_errors.UnexpectedAttribute(
          'Unexpected attribute \'%s\' for object of type %s.' %
          (key, str(subject.value.__class__)))

    if isinstance(value, _ObjectMapper):
      value.set_value(subject.value.GetAttribute(key).expected_type())
      value = value.value
    elif isinstance(value, _ObjectSequencer):
      value.set_constructor(self._GetRepeated(subject.value.ATTRIBUTES[key]))
      value = value.value

    subject.see(key)
    try:
      setattr(subject.value, key, value)
    except validation.ValidationError, e:
      try:
        error_str = str(e)
      except Exception:
        error_str = '<unknown>'

      try:
        value_str = str(value)
      except Exception:
        value_str = '<unknown>'

      e.message = ("Unable to assign value '%s' to attribute '%s':\n%s" %
                   (value_str, key, error_str))
      raise e
    except Exception, e:
      try:
        error_str = str(e)
      except Exception:
        error_str = '<unknown>'

      try:
        value_str = str(value)
      except Exception:
        value_str = '<unknown>'

      message = ("Unable to assign value '%s' to attribute '%s':\n%s" %
                 (value_str, key, error_str))
      raise validation.ValidationError(message, e)

  def AppendTo(self, subject, value):
    """Append a value to a sequence.

    Args:
      subject: _ObjectSequence that is receiving new value.
      value: Value that is being appended to sequence.
    """
    if isinstance(value, _ObjectMapper):
      value.set_value(subject.constructor())
      subject.value.append(value.value)
    else:
      subject.value.append(value)


def BuildObjects(default_class, stream, loader=yaml.loader.SafeLoader):
  """Build objects from stream.

  Handles the basic case of loading all the objects from a stream.

  Args:
    default_class: Class that is instantiated upon the detection of a new
      document.  An instance of this class will act as the document itself.
    stream: String document or open file object to process as per the
      yaml.parse method.  Any object that implements a 'read()' method which
      returns a string document will work with the YAML parser.
    loader_class: Used for dependency injection.

  Returns:
    List of default_class instances parsed from the stream.
  """
  builder = ObjectBuilder(default_class)
  handler = yaml_builder.BuilderHandler(builder)
  listener = yaml_listener.EventListener(handler)

  listener.Parse(stream, loader)
  return handler.GetResults()


def BuildSingleObject(default_class, stream, loader=yaml.loader.SafeLoader):
  """Build object from stream.

  Handles the basic case of loading a single object from a stream.

  Args:
    default_class: Class that is instantiated upon the detection of a new
      document.  An instance of this class will act as the document itself.
    stream: String document or open file object to process as per the
      yaml.parse method.  Any object that implements a 'read()' method which
      returns a string document will work with the YAML parser.
    loader_class: Used for dependency injection.
  """
  definitions = BuildObjects(default_class, stream, loader)

  if len(definitions) < 1:
    raise yaml_errors.EmptyConfigurationFile()
  if len(definitions) > 1:
    raise yaml_errors.MultipleConfigurationFile()
  return definitions[0]
