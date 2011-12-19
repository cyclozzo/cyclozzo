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

"""Errors used in the Python datastore API."""






class Error(Exception):
  """Base datastore error type.
  """

class BadValueError(Error):
  """Raised by Entity.__setitem__(), Query.__setitem__(), Get(), and others
  when a property value or filter value is invalid.
  """

class BadPropertyError(Error):
  """Raised by Entity.__setitem__() when a property name isn't a string.
  """

class BadRequestError(Error):
  """Raised by datastore calls when the parameter(s) are invalid.
  """

class EntityNotFoundError(Error):
  """DEPRECATED: Raised by Get() when the requested entity is not found.
  """

class BadArgumentError(Error):
  """Raised by Query.Order(), Iterator.Next(), and others when they're
  passed an invalid argument.
  """

class QueryNotFoundError(Error):
  """DEPRECATED: Raised by Iterator methods when the Iterator is invalid. This
  should not happen during normal usage; it protects against malicious users
  and system errors.
  """

class TransactionNotFoundError(Error):
  """DEPRECATED: Raised by RunInTransaction. This is an internal error; you
  should not see this.
  """

class Rollback(Error):
  """May be raised by transaction functions when they want to roll back
  instead of committing. Note that *any* exception raised by a transaction
  function will cause a rollback. This is purely for convenience. See
  datastore.RunInTransaction for details.
  """

class TransactionFailedError(Error):
  """Raised by RunInTransaction methods when the transaction could not be
  committed, even after retrying. This is usually due to high contention.
  """

class BadFilterError(Error):
  """Raised by Query.__setitem__() and Query.Run() when a filter string is
  invalid.
  """
  def __init__(self, filter):
    self.filter = filter

  def __str__(self):
    return (u'BadFilterError: invalid filter: %s.' % self.filter)

class BadQueryError(Error):
  """Raised by Query when a query or query string is invalid.
  """

class BadKeyError(Error):
  """Raised by Key.__str__ when the key is invalid.
  """

class InternalError(Error):
  """An internal datastore error. Please report this to Google.
  """

class NeedIndexError(Error):
  """No matching index was found for a query that requires an index. Check
  the Indexes page in the Admin Console and your index.yaml file.
  """

class Timeout(Error):
  """The datastore operation timed out, or the data was temporarily
  unavailable. This can happen when you attempt to put, get, or delete too
  many entities or an entity with too many properties, or if the datastore is
  overloaded or having trouble.
  """

class CommittedButStillApplying(Timeout):
  """The write or transaction was committed, but some entities or index rows
  may not have been fully updated. Those updates should automatically be
  applied soon. You can roll them forward immediately by reading one of the
  entities inside a transaction.
  """
