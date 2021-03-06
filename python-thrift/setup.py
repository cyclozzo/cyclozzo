#!/usr/bin/env python

#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements. See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership. The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License. You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied. See the License for the
# specific language governing permissions and limitations
# under the License.
#

from setuptools import setup, Extension

fastbinarymod = Extension('thrift.protocol.fastbinary',
                          sources = ['thrift/protocol/fastbinary.c'],
                          )

setup(name = 'Thrift',
      version = '0.6.1',
      description = 'Python bindings for the Apache Thrift RPC system',
      author = ['Thrift Developers'],
      author_email = ['dev@thrift.apache.org'],
      url = 'http://thrift.apache.org',
      license = 'Apache License 2.0',
      packages = [
        'thrift',
        'thrift.protocol',
        'thrift.transport',
        'thrift.server',
      ],
      #package_dir = {'thrift' : 'src'},
      ext_modules = [fastbinarymod],
      )

