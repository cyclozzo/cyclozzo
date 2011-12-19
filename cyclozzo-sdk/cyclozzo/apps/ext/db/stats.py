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

"""Models to be used when accessing app specific datastore usage statistics.

These entities cannot be created by users, but are populated in the
application's datastore by offline processes run by the Google App Engine team.
"""




from cyclozzo.apps.ext import db


class BaseStatistic(db.Model):
  """Base Statistic Model class.

  The 'bytes' attribute represents the total number of bytes taken up in the
  datastore for the statistic instance.  The 'count' attribute is the
  total number of occurrences of the statistic in the datastore.  The
  'timestamp' is when the statistic instance was written to the datastore.
  """
  STORED_KIND_NAME = '__BaseStatistic__'

  bytes = db.IntegerProperty()

  count = db.IntegerProperty()

  timestamp = db.DateTimeProperty()

  @classmethod
  def kind(cls):
    """Kind name override."""
    return cls.STORED_KIND_NAME


class BaseKindStatistic(BaseStatistic):
  """Base Statistic Model class for stats associated with kinds.

  The 'kind_name' attribute represents the name of the kind associated with the
  statistic instance.
  """
  STORED_KIND_NAME = '__BaseKindStatistic__'

  kind_name = db.StringProperty()


class GlobalStat(BaseStatistic):
  """An aggregate of all entities across the entire application.

  This statistic only has a single instance in the datastore that contains the
  total number of entities stored and the total number of bytes they take up.
  """
  STORED_KIND_NAME = '__Stat_Total__'


class KindStat(BaseKindStatistic):
  """An aggregate of all entities at the granularity of their Kind.

  There is an instance of the KindStat for every Kind that is in the
  application's datastore.  This stat contains per-Kind statistics.
  """
  STORED_KIND_NAME = '__Stat_Kind__'


class KindRootEntityStat(BaseKindStatistic):
  """Statistics of the number of root entities in the datastore by Kind.

  There is an instance of the KindRootEntityState for every Kind that is in the
  application's datastore and has an instance that is a root entity.  This stat
  contains statistics regarding these root entity instances.
  """
  STORED_KIND_NAME = '__Stat_Kind_IsRootEntity__'


class KindNonRootEntityStat(BaseKindStatistic):
  """Statistics of the number of non root entities in the datastore by Kind.

  There is an instance of the KindNonRootEntityStat for every Kind that is in
  the application's datastore that is a not a root entity.  This stat contains
  statistics regarding thse non root entity instances.
  """
  STORED_KIND_NAME = '__Stat_Kind_NotRootEntity__'


class PropertyTypeStat(BaseStatistic):
  """An aggregate of all properties across the entire application by type.

  There is an instance of the PropertyTypeStat for every property type
  (cyclozzo.apps.api.datastore_types._PROPERTY_TYPES) in use by the
  application in its datastore.
  """
  STORED_KIND_NAME = '__Stat_PropertyType__'

  property_type = db.StringProperty()


class KindPropertyTypeStat(BaseKindStatistic):
  """Statistics on (kind, property_type) tuples in the app's datastore.

  There is an instance of the KindPropertyTypeStat for every
  (kind, property_type) tuple in the application's datastore.
  """
  STORED_KIND_NAME = '__Stat_PropertyType_Kind__'

  property_type = db.StringProperty()


class KindPropertyNameStat(BaseKindStatistic):
  """Statistics on (kind, property_name) tuples in the app's datastore.

  There is an instance of the KindPropertyNameStat for every
  (kind, property_name) tuple in the application's datastore.
  """
  STORED_KIND_NAME = '__Stat_PropertyName_Kind__'

  property_name = db.StringProperty()


class KindPropertyNamePropertyTypeStat(BaseKindStatistic):
  """Statistic on (kind, property_name, property_type) tuples in the datastore.

  There is an instance of the KindPropertyNamePropertyTypeStat for every
  (kind, property_name, property_type) tuple in the application's datastore.
  """
  STORED_KIND_NAME = '__Stat_PropertyType_PropertyName_Kind__'

  property_type = db.StringProperty()

  property_name = db.StringProperty()
