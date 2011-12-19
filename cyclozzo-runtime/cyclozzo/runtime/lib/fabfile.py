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
# Hypertable & Hadoop Deployment using Fabric
#   Reference: 
#   https://github.com/nuggetwheat/hypertable/blob/master/conf/Capfile.cluster
#
# @author: Sreejith K
# @date: 14 Oct 2011


import os
import sys

from fabric.api import run, local, env, settings
from fabric.decorators import roles, task
from fabric.network import disconnect_all


DEFAULT_HT_INSTALL_DIR          = '/opt/hypertable'
DEFAULT_HYPERTABLE_VERSION      = '0.9.5.0.pre6'
DEFAULT_HT_CONFIG               = '/etc/cyclozzo/hypertable.cfg'
DEFAULT_DFS		                = 'hadoop'

DEFAULT_HADOOP_INSTALL_DIR      = '/usr/lib/hadoop'
DEFAULT_HADOOP_CONFIG_DIR       = '/etc/cyclozzo'


def update_roles(config):
    """Update the Fabric runtime environment with roles.
    """
    env.cyclozzo_config = config
    env.roledefs['source'] = [config.master]
    env.roledefs['master'] = [config.master]
    env.roledefs['hyperspace'] = [config.master]
    env.roledefs['thriftbroker'] = [config.master]
    env.roledefs['slave'] = config.slaves


def ht_install_dir():
    """Return Hypertable install directory
    """
    return env.cyclozzo_config.ht_install_dir or DEFAULT_HT_INSTALL_DIR


def ht_version():
    """Return Hypertable version
    """
    return env.cyclozzo_config.ht_version or DEFAULT_HYPERTABLE_VERSION


def ht_config():
    """Return Hypertable config filename
    """
    return env.cyclozzo_config.ht_config or DEFAULT_HT_CONFIG


def ht_config_option():
    """Return configuration option for Hypertable
    """
    return '--config=%s' % ht_config()


def dfs_type():
    """Return DFS type
    """
    return env.cyclozzo_config.dfs or DEFAULT_DFS


def hadoop_install_dir():
    """Return Hadoop installation directory
    """
    return env.cyclozzo_config.hadoop_install_dir or DEFAULT_HADOOP_INSTALL_DIR


def hadoop_config_dir():
    """Return Hadoop config directory
    """
    return env.cyclozzo_config.hadoop_config_dir or DEFAULT_HADOOP_CONFIG_DIR


def hadoop_config_option():
    """Return configuration option for Hadoop
    """
    return '--config %s' % hadoop_config_dir()


###############################################################################
# Task definitions for `fab` tool. Use them using `fab <alias>`
###############################################################################


@task(alias='exchange-keys')
def _exchange_keys():
    """SSH key exchange
    """
    for host in env.roledefs['slave']:
        local('ssh-copy-id -i ~/.ssh/id_dsa.pub cyclozzo@%s' % host)


@task(alias='rsync')
def _rsync():
    """rsyncs the hypertable and hadoop configuration to slaves.
    """
    for host in env.roledefs['slave']:
        local('rsync -rtzh --progress --delete /etc/cyclozzo/ %s:/etc/cyclozzo/' % host)


@task(alias='start-hyperspace')
@roles('hyperspace')
def _start_hyperspace():
    """Starts hyperspace process
    """
    run('%s/bin/hadoop dfsadmin -safemode wait' % hadoop_install_dir())
    run('%s/%s/bin/start-hyperspace.sh %s'
        % (ht_install_dir(), ht_version(), ht_config_option()), pty=False
        )


@task(alias='stop-hyperspace')
@roles('hyperspace')
def _stop_hyperspace():
    """Stop all hyperspace services
    """
    run( '%s/%s/bin/stop-hyperspace.sh' % (ht_install_dir(), ht_version()))


@task(alias='start-ht-master')
@roles('master')
def _start_ht_master():
    """Starts hypertable master process
    """
    run('%s/%s/bin/start-master.sh %s'
        % (ht_install_dir(), ht_version(), ht_config_option()), pty=False
        )


@task(alias='stop-ht-master')
@roles('master')
def _stop_ht_master():
    """Stop hypertable master service
    """
    run('%s/%s/bin/stop-servers.sh --no-hyperspace --no-rangeserver ' \
        '--no-dfsbroker --no-thriftbroker' % (ht_install_dir(), ht_version())
        )


@task(alias='start-rangeservers')
@roles('slave')
def _start_rangeservers():
    """Starts all the hypertable slave processes.
    """
    run('%s/%s/bin/start-rangeserver.sh %s'
        % (ht_install_dir(), ht_version(), ht_config_option()), 
        pty=False
        )


@task(alias='stop-rangeservers')
@roles('slave')
def _stop_rangeservers():
    """Stop all the hypertable slave services
    """
    run('%s/%s/bin/stop-servers.sh --no-hyperspace --no-master ' \
        '--no-dfsbroker --no-thriftbroker' % (ht_install_dir(), ht_version())
        )


@task(alias='start-dfsbrokers')
@roles('master', 'slave')
def _start_dfsbrokers():
    """Starts DFS broker
    """
    run('%s/%s/bin/start-dfsbroker.sh %s %s'
        % (ht_install_dir(), ht_version(), dfs_type(), ht_config_option()), 
        pty=False
        )


@task(alias='stop-dfsbrokers')
@roles('master', 'slave')
def _stop_dfsbrokers():
    """Stop all the dfsbrokers
    """
    run('%s/%s/bin/stop-servers.sh --no-hyperspace --no-master ' \
        '--no-rangeserver' % (ht_install_dir(), ht_version()))


@task(alias='start-thriftbrokers')
@roles('thriftbroker')
def _start_thriftbrokers():
    """Starts thriftbroker on master.
    """
    run('%s/%s/bin/start-thriftbroker.sh %s'
        % (ht_install_dir(), ht_version(), ht_config_option()), 
        pty=False
        )


@task(alias='stop-thriftbrokers')
@roles('thriftbroker')
def _stop_thriftbrokers():
    """Stop all the thriftbrokers
    """
    run('%s/%s/bin/stop-servers.sh --no-hyperspace --no-master ' \
        '--no-rangeserver --no-dfsbroker' % (ht_install_dir(), ht_version())
        )


@task(alias='format-hypertable')
@roles('master')
def _format_hypertable():
    """Format Hypertable
    """
    run('%s/bin/hadoop dfsadmin -safemode wait' % hadoop_install_dir())
    with settings(warn_only=True):
        run('%s/bin/hadoop fs -rmr /hypertable' % hadoop_install_dir())
    run('%s/bin/hadoop fs -mkdir /hypertable' % hadoop_install_dir())
    run('%s/bin/hadoop fs -chmod 777 /hypertable' % hadoop_install_dir())
    run('%s/%s/bin/clean-database.sh' % (ht_install_dir(), ht_version()))
    run('%s/%s/bin/clean-hyperspace.sh' % (ht_install_dir(), ht_version()))


@task(alias='start-hadoop-namenode')
@roles('master')
def _start_hadoop_namenode():
    """Start hadoop master
    """
    run('%s/bin/hadoop-daemon.sh %s start namenode' 
        %(hadoop_install_dir(), hadoop_config_option()), pty=False
        )


@task(alias='stop-hadoop-namenode')
@roles('master')
def _stop_hadoop_namenode():
    """Stop hadoop master
    """
    run('%s/bin/hadoop-daemon.sh %s stop namenode'
        %(hadoop_install_dir(), hadoop_config_option()), pty=False
        )


@task(alias='format-hadoop-namenode')
@roles('master')
def _format_hadoop_namenode():
    """Format hadoop master
    """
    run('rm -rf /var/cyclozzo/dfs/name/*')
    run('%s/bin/hadoop namenode -format' % hadoop_install_dir(), pty=False
        )


@task(alias='start-hadoop-datanode')
@roles('master', 'slave')
def _start_hadoop_datanode():
    """Start hadoop slave
    """
    run('%s/bin/hadoop-daemon.sh %s start datanode'
        %(hadoop_install_dir(), hadoop_config_option()), pty=False
        )


@task(alias='stop-hadoop-datanode')
@roles('master', 'slave')
def _stop_hadoop_datanode():
    """Stop hadoop slave
    """
    run('%s/bin/hadoop-daemon.sh %s stop datanode'
        %(hadoop_install_dir(), hadoop_config_option()), pty=False
        )


@task(alias='format-hadoop-datanode')
@roles('master', 'slave')
def _format_hadoop_datanode():
    """Format hadoop master
    """
    run('rm -rf /var/cyclozzo/dfs/data/*')
    run('%s/bin/hadoop datanode -format' % hadoop_install_dir(), pty=False)


@task(alias='start')
def _start():
    """Start all services.
    """
    _start_hadoop_namenode()
    _start_hadoop_datanode()
    _start_dfsbrokers()
    _start_hyperspace()
    _start_ht_master()
    _start_rangeservers()
    _start_thriftbrokers()


@task(alias='stop')
def _stop():
    """Stop all services.
    """
    _stop_thriftbrokers()
    _stop_ht_master()
    _stop_rangeservers()
    _stop_dfsbrokers()
    _stop_hyperspace()    
    _stop_hadoop_datanode()
    _stop_hadoop_namenode()



###############################################################################
# The Following functions can be imported and used in any Python module
###############################################################################


def exchange_keys():
    """SSH key exchange
    """
    _exchange_keys()


def rsync():
    """rsyncs the config files to slaves
    """
    _rsync()


def start_hyperspace():
    """Starts hyperspace process
    """
    for host in env.roledefs['hyperspace']:
        with settings(host_string=host):
            _start_hyperspace()


def stop_hyperspace():
    """Stop all hyperspace services
    """
    for host in env.roledefs['hyperspace']:
        with settings(host_string=host):
            _stop_hyperspace()
    

def start_ht_master():
    """Starts hypertable master process
    """
    for host in env.roledefs['master']:
        with settings(host_string=host):
            _start_ht_master()


def stop_ht_master():
    """Stop hypertable master service
    """
    for host in env.roledefs['master']:
        with settings(host_string=host):
            _stop_ht_master()


def start_rangeservers():
    """Starts all the hypertable slave processes.
    """
    for host in env.roledefs['slave']:
        with settings(host_string=host):
            _start_rangeservers()


def stop_rangeservers():
    """Stop all slave services.
    """
    for host in env.roledefs['slave']:
        with settings(host_string=host):
            _stop_rangeservers()


def start_dfsbrokers():
    """Start DFS brokers on all nodes.
    """
    for host in (env.roledefs['master'] +  env.roledefs['slave']):
        with settings(host_string=host):
            _start_dfsbrokers()


def stop_dfsbrokers():
    """Stop all dfsbrokers.
    """
    for host in (env.roledefs['master'] +  env.roledefs['slave']):
        with settings(host_string=host):
            _stop_dfsbrokers()


def start_thriftbrokers():
    """Starts thriftbroker on master.
    """
    for host in env.roledefs['thriftbroker']:
        with settings(host_string=host):
            _start_thriftbrokers()


def stop_thriftbrokers():
    """Stop all thriftbrokers.
    """
    for host in env.roledefs['thriftbroker']:
        with settings(host_string=host):
            _stop_thriftbrokers()


def format_hypertable():
    for host in env.roledefs['master']:
        with settings(host_string=host):
            _format_hypertable()


def start_hadoop_namenode():
    for host in env.roledefs['master']:
        with settings(host_string=host):
            _start_hadoop_namenode()


def stop_hadoop_namenode():
    for host in env.roledefs['master']:
        with settings(host_string=host):
            _stop_hadoop_namenode()


def format_hadoop_namenode():
    for host in env.roledefs['master']:
        with settings(host_string=host):
            _format_hadoop_namenode()


def start_hadoop_datanode():
    for host in env.roledefs['master'] + env.roledefs['slave']:
        with settings(host_string=host):
            _start_hadoop_datanode()


def stop_hadoop_datanode():
    for host in  env.roledefs['master'] + env.roledefs['slave']:
        with settings(host_string=host):
            _stop_hadoop_datanode()


def format_hadoop_datanode():
    for host in  env.roledefs['master'] + env.roledefs['slave']:
        with settings(host_string=host):
            _format_hadoop_datanode()


def start():
    """Start all services.
    """
    start_hadoop_namenode()
    start_hadoop_datanode()
    start_dfsbrokers()
    start_hyperspace()
    start_ht_master()
    start_rangeservers()
    start_thriftbrokers()


def stop():
    """Stop all services.
    """
    stop_thriftbrokers()
    stop_ht_master()
    stop_rangeservers()
    stop_dfsbrokers()
    stop_hyperspace()
    stop_hadoop_datanode()
    stop_hadoop_namenode()

 
#if __name__ == '__main__':
#    # use as python library
#    # use with fab tool
#    from cyclozzo.runtime.lib.config import ApplicationConfiguration
#    import cyclozzo
#    config_file = os.path.join(os.path.dirname(os.path.abspath(cyclozzo.__file__)), 
#                               'lite/settings.yaml')
#    update_roles(config)
#    if len(sys.argv) < 2:
#        action = 'dist'
#    else:
#        action = sys.argv[1]
#    print '--> Running action', action
#    globals().get(action, 'dist')()
#    #disconnect_all()
#else:
#    # use with fab tool
#    from cyclozzo.runtime.lib.config import ApplicationConfiguration
#    import cyclozzo
#    config_file = os.path.join(os.path.dirname(os.path.abspath(cyclozzo.__file__)), 
#                               'lite/settings.yaml')
#    config = ApplicationConfiguration(config_file)
#    update_roles(config)

