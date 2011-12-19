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
#Author: Anoop Joe Cyriac

import tarfile
import os
import logging

log = logging.getLogger(__name__)
_Tmp_dir = '/tmp/cyclozzo/archive/'
_Type_dic = {'bz2' : {
                   'suffix' : '.tar.bz2',
                   'mode' : ':bz2'
                   },
            'gz' : {
                   'suffix' : '.tar.gz',
                   'mode' : ':gz'
                   },
            'tar' : {
                   'suffix' : '.tar',
                   'mode' : ':*'
                   }
            }

def pack(path2tar, dest_file='', include_cur=False, type='bz2'):
    '''@path2tar dir structure is preserved while extracting.'''
    global _Tmp_dir, _Type_dic

    # Without 'dest_file' dest dir is '_Tmp_dir' + basename('path2tar')
    if not dest_file:
        dest_file = _Tmp_dir +  os.path.basename(os.path.abspath(path2tar))

    # Created file always have proper suffix
    if not dest_file.endswith(_Type_dic[type]['suffix']):
        dest_file = dest_file + _Type_dic[type]['suffix']

    # Create dest dir if absent
    if not os.path.exists(os.path.split(os.path.abspath(dest_file))[0]):
        os.makedirs(os.path.split(os.path.abspath(dest_file))[0])

    # To specify if the specified path's base dir also need to be added or 
    #   only what inside the dir.
    if include_cur == False:
        arcname = '.'
    else:
        arcname = os.path.basename(os.path.abspath(path2tar))

    t_fp = tarfile.open(dest_file, 'w' + _Type_dic[type]['mode'])
    t_fp.add(path2tar, arcname=arcname)
    t_fp.close()
    log.debug('Created tar file: %s' % dest_file)

    return dest_file

def unpack(tar_file, dest_dir=_Tmp_dir, type='bz2'):
    global _Tmp_dir, _Type_dic

    # @dest_dir same as tar file name under 'dest_dir'
    dest_dir +=  '/' + os.path.split(os.path.abspath(tar_file))[1] \
                                            [:-len(_Type_dic[type]['suffix'])]
    # Unpacked always under '_Tmp_dir'
    if not dest_dir.startswith(_Tmp_dir):
            dest_dir = _Tmp_dir + dest_dir

    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)
    dest_dir = os.path.normpath(dest_dir)
    t_fp = tarfile.open(tar_file, 'r' + _Type_dic[type]['mode'])
    t_fp.extractall(dest_dir)
    t_fp.close()
    log.debug('Extracted tar file: %s to %s' % (tar_file, dest_dir))
    
    return dest_dir

if __name__ == '__main__':
    dest_file = pack('/home/ajc/src/cyclozzo')
    print 'Tarred to %(dest_file)s' %locals()
    # Tarred to /tmp/cyclozzo/archive/cyclozzo.tar.bz2
    #   Contents will be like 
    #       ./********
    dest_dir = unpack(dest_file, '/tmp/cyclozzo/x')
    print 'Extracted to %(dest_dir)s' %locals()
    # Extracted to /tmp/cyclozzo/archive/tmp/cyclozzo/x/cyclozzo

    dest_file = pack('/home/ajc/src/cyclozzo', include_cur=True)
    print 'Tarred to %(dest_file)s' %locals()
    # Tarred to /tmp/cyclozzo/archive/cyclozzo.tar.bz2
    #   Contents will be like 
    #       cyclozzo/******
    dest_dir = unpack(dest_file, '/tmp/cyclozzo/x1')
    print 'Extracted to %(dest_dir)s' %locals()
    # Extracted to /tmp/cyclozzo/archive/tmp/cyclozzo/x/cyclozzo

    dest_file = pack('/home/ajc/src/cyclozzo')
    print 'Tarred to %(dest_file)s' %locals()
    # Tarred to /tmp/cyclozzo/archive/cyclozzo.tar.bz2
    #   Contents will be like 
    #       ./********
    dest_dir = unpack(dest_file)
    print 'Extracted to %(dest_dir)s' %locals()
    # Extracted to /tmp/cyclozzo/archive/cyclozzo
