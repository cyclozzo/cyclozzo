#!/usr/bin/env python
#
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
# Contains implementation of blobstore_stub.BlobStorage that writes
# blobs directly to HDFS (Hadoop Distributed FileSystem).
#
# @author: Sreejith K
# Created on 18th Apr 2011


import errno
import os

from cyclozzo.runtime.lib.hadoopfs import HadoopClient, HadoopFile
from cyclozzo.runtime.lib.genhadoopfs.ttypes import Pathname
from cyclozzo.apps.api import blobstore
from cyclozzo.apps.api.blobstore import blobstore_stub


__all__ = ['HdfsBlobStorage']


class HdfsBlobStorage(blobstore_stub.BlobStorage):
  """Storage mechanism for storing blob data on HDFS."""

  def __init__(self, server, port, storage_directory, app_id):
    """Constructor.

    Args:
      server: HDFS server address
      port: HDFS listen port
      storage_directory: Directory within which to store blobs.
      app_id: App id to store blobs on behalf of.
    """
    self._server = server
    self._port = port
    self._storage_directory = storage_directory
    self._app_id = app_id
    # connect to HDFS
    self._fs = HadoopClient(self._server, self._port)

  @classmethod
  def _BlobKey(cls, blob_key):
    """Normalize to instance of BlobKey."""
    if not isinstance(blob_key, blobstore.BlobKey):
      return blobstore.BlobKey(unicode(blob_key))
    return blob_key

  def _DirectoryForBlob(self, blob_key):
    """Determine which directory where a blob is stored.

    Each blob gets written to a directory underneath the storage objects
    storage directory based on the blobs kind, app-id and first character of
    its name.  So blobs with blob-keys:

      _ACFDEDG
      _MNOPQRS
      _RSTUVWX

    Are stored in:

      <storage-dir>/blob/myapp/A
      <storage-dir>/blob/myapp/M
      <storage-dir>/R

    Args:
      blob_key: Blob key to determine directory for.

    Returns:
      Directory relative to this objects storage directory to
      where blob is stored or should be stored.
    """
    blob_key = self._BlobKey(blob_key)
    return os.path.join(self._storage_directory,
                        self._app_id,
                        str(blob_key)[1])

  def _FileForBlob(self, blob_key):
    """Calculate full filename to store blob contents in.

    This method does not check to see if the file actually exists.

    Args:
      blob_key: Blob key of blob to calculate file for.

    Returns:
      Complete path for file used for storing blob.
    """
    blob_key = self._BlobKey(blob_key)
    return os.path.join(self._DirectoryForBlob(blob_key), str(blob_key)[1:])

  def StoreBlob(self, blob_key, blob_stream):
    """Store blob stream to disk.

    Args:
      blob_key: Blob key of blob to store.
      blob_stream: Stream or stream-like object that will generate blob content.
    """
    blob_key = self._BlobKey(blob_key)
    blob_directory = Pathname(self._DirectoryForBlob(blob_key))
    if not self._fs.exists(blob_directory):
      self._fs.mkdirs(blob_directory)
    blob_file = self._FileForBlob(blob_key)
    hdfs_file = HadoopFile(self._server, self._port, blob_file, 'w')

    try:
      while True:
        block = blob_stream.read(1 << 20)
        if not block:
          break
        hdfs_file.write(block)
    finally:
      hdfs_file.close()

  def OpenBlob(self, blob_key):
    """Open blob file for streaming.

    Args:
      blob_key: Blob-key of existing blob to open for reading.

    Returns:
      Open file stream for reading blob from disk.
    """
    return HadoopFile(self._server, self._port, self._FileForBlob(blob_key), 'r')

  def DeleteBlob(self, blob_key):
    """Delete blob data from disk.

    Deleting an unknown blob will not raise an error.

    Args:
      blob_key: Blob-key of existing blob to delete.
    """
    self._fs.rm(Pathname(self._FileForBlob(blob_key)), recursive=True)
