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
# Script to manage Cyclozzo Nodes
#
# @authors: Sreejith K, Vishnusaran M
# Created On 11th Oct 2011


import os, sys
from optparse import OptionParser
from time import sleep
import shutil
import signal

from cyclozzo.runtime.lib import fabfile
from cyclozzo.runtime.lib.config import ApplicationConfiguration
from cyclozzo import appserver

from cyclozzo.appserver import appserver as appsrv
appsrv.fix_sys_path()

from cyclozzo.appserver.server import AppDaemon


HT_METADATA_TEMPLATE = """
<Schema>
  <AccessGroup name="default">
    <ColumnFamily>
      <Name>LogDir</Name>
    </ColumnFamily>
    <ColumnFamily>
      <Name>Files</Name>
    </ColumnFamily>
  </AccessGroup>
  <AccessGroup name="location" inMemory="true">
    <ColumnFamily>
      <Name>StartRow</Name>
      <MaxVersions>5</MaxVersions>
    </ColumnFamily>
    <ColumnFamily>
      <Name>Location</Name>
      <MaxVersions>5</MaxVersions>
    </ColumnFamily>
  </AccessGroup>
  <AccessGroup name="logging">
    <ColumnFamily>
      <Name>Event</Name>
    </ColumnFamily>
  </AccessGroup>
</Schema>

"""


HT_CONFIG_TEMPLATE = """
# Global properties
Hypertable.Request.Timeout=180000

# HDFS Broker
# Access to master HDFS
HdfsBroker.Port=38030
HdfsBroker.fs.default.name=hdfs://%s:9000
HdfsBroker.Workers=20

#Access to local hadoop instance 
#for both master and slave
DfsBroker.Host=localhost
DfsBroker.Port=38030

# Hyperspace
%s
Hyperspace.Replica.Port=38040
Hyperspace.Replica.Dir=/var/cyclozzo/hyperspace
Hyperspace.Replica.Workers=20

# Hypertable.Master
Hypertable.Master.Host=%s
Hypertable.Master.Port=38050
Hypertable.Master.Workers=20

# Hypertable.RangeServer
Hypertable.RangeServer.Port=38060

Hyperspace.KeepAlive.Interval=30000
Hyperspace.Lease.Interval=1000000
Hyperspace.GracePeriod=200000

# ThriftBroker
ThriftBroker.Port=38080
"""


RS_METRICS_TEMPLATE = """
<Schema generation="1">
  <AccessGroup name="server">
    <ColumnFamily id="1">
      <Generation>1</Generation>
      <Name>server</Name>
      <Counter>false</Counter>
      <MaxVersions>336</MaxVersions>
      <deleted>false</deleted>
    </ColumnFamily>
  </AccessGroup>
  <AccessGroup name="range">
    <ColumnFamily id="2">
      <Generation>1</Generation>
      <Name>range</Name>
      <Counter>false</Counter>
      <MaxVersions>24</MaxVersions>
      <deleted>false</deleted>
    </ColumnFamily>
    <ColumnFamily id="3">
      <Generation>1</Generation>
      <Name>range_start_row</Name>
      <Counter>false</Counter>
      <MaxVersions>1</MaxVersions>
      <deleted>false</deleted>
    </ColumnFamily>
    <ColumnFamily id="4">
      <Generation>1</Generation>
      <Name>range_move</Name>
      <Counter>false</Counter>
      <MaxVersions>1</MaxVersions>
      <deleted>false</deleted>
    </ColumnFamily>
  </AccessGroup>
</Schema>
"""


HDFS_SITE_TEMPLATE = """
<configuration>
    <property>
        <name>dfs.name.dir</name>
        <value>/var/cyclozzo/dfs/name</value>
    </property>
    <property>
        <name>dfs.data.dir</name>
        <value>/var/cyclozzo/dfs/data</value>
    </property>
</configuration>
"""


CORE_SITE_TEMPLATE = """
<configuration>
    <property>
        <name>fs.default.name</name>
        <value>hdfs://%s:9000</value>
    </property>
</configuration>
"""


def configure_hypertable(primary='127.0.0.1', secondary=[]):
    """Configure Hypertable
    """
    hypertable_path = '/opt/hypertable/current'
    hyperspace_cfg = 'Hyperspace.Replica.Host=%s' % primary
    with open('/etc/cyclozzo/hypertable.cfg', 'w') as f:
        f.write(HT_CONFIG_TEMPLATE % (primary, hyperspace_cfg, primary))

    if not os.path.exists('/etc/cyclozzo/METADATA.xml'):
        print 'Getting METADATA'
        if os.path.exists(os.path.join(hypertable_path, 'conf', 'METADATA.xml')):
            meta_path = os.path.join(hypertable_path, 'conf', 'METADATA.xml')
        elif os.path.exists(os.path.join(hypertable_path, 'conf.backup', 'METADATA.xml')):
            meta_path = os.path.join(hypertable_path, 'conf.backup', 'METADATA.xml')
        else:
            meta_path = None
        if meta_path:
            print 'Using metadata for DS from %s' % meta_path
            if os.system('cp -f %s /etc/cyclozzo/METADATA.xml' % meta_path ) != 0:
                print 'Failed to copy!'
                sys.exit(-1)
        else:
            with open('/etc/cyclozzo/METADATA.xml', 'w') as f:
                f.write(HT_METADATA_TEMPLATE)

    if not os.path.exists('/etc/cyclozzo/RS_METRICS.xml'):
        with open('/etc/cyclozzo/RS_METRICS.xml', 'w') as f:
            f.write(RS_METRICS_TEMPLATE)

    print 'Creating symlinks'
    os.system('rm -rf %s' % os.path.join(hypertable_path, 'log'))
    os.system('rm -rf %s' % os.path.join(hypertable_path, 'run'))
    if not os.path.exists(os.path.join(hypertable_path, 'conf.backup')):
        print 'SysConf: Backup default DS conf to %s' % os.path.join(hypertable_path, 'conf.backup')
        os.system('mv %s %s' % (os.path.join(hypertable_path, 'conf'), os.path.join(hypertable_path, 'conf.backup')) )
    os.system('rm -rf %s' % os.path.join(hypertable_path, 'conf'))
    os.system('rm -rf %s' % os.path.join(hypertable_path, 'fs'))
    os.system('rm -rf %s' % os.path.join(hypertable_path, 'hyperspace'))
    os.system('ln -s /var/cyclozzo/hyperspace %s' % os.path.join(hypertable_path, 'hyperspace'))
    os.system('ln -s /var/cyclozzo/logs %s' % os.path.join(hypertable_path, 'log'))
    os.system('ln -s /var/cyclozzo/logs %s' % os.path.join(hypertable_path, 'run'))
    os.system('ln -s /etc/cyclozzo %s' % os.path.join(hypertable_path, 'conf'))


def configure_hadoop(primary='127.0.0.1', secondary=[]):
    """Configure Hadoop
    """
    with open('/etc/cyclozzo/hadoop-env.sh', 'w') as f:
        f.write('export JAVA_HOME=/usr/lib/jvm/java-6-sun\n')
    
    with open('/etc/cyclozzo/hdfs-site.xml', 'w') as f:
        f.write(HDFS_SITE_TEMPLATE)
    
    with open('/etc/cyclozzo/core-site.xml', 'w') as f:
        f.write(CORE_SITE_TEMPLATE % primary)
    
    with open('/etc/cyclozzo/masters', 'w') as f:
        f.write(primary +'\n')
        
    with open('/etc/cyclozzo/slaves', 'w') as f:
        f.write(primary +'\n')
        for s in secondary:
            f.write(s + '\n')

    print 'Creating links for DFS to /var/cyclozzo'
    from cyclozzo.runtime.lib.cmnd import run_command
    rc, out = run_command(['rm', '-f' , '/usr/lib/hadoop/logs'])
    if rc != 0:
        print 'Failed to configure DFS, code = %s : %s' % (rc, out)
        sys.exit(-1)
    rc, out = run_command(['rm', '-f' , '/usr/lib/hadoop/pids'])
    if rc != 0:
        print 'Failed to configure DFS, code = %s : %s' % (rc, out)
        sys.exit(-1)
    rc, out = run_command(['rm', '-f' , '/usr/lib/hadoop/conf'])
    if rc != 0:
        print'Failed to configure DFS, code = %s : %s' % (rc, out)
        sys.exit(-1)
    
    rc, out = run_command(['ln', '-s' , '/var/cyclozzo/logs/', '/usr/lib/hadoop/logs'])
    if rc != 0:
        print 'Failed to configure DFS, code = %s : %s' % (rc, out)
        sys.exit(-1)
    rc, out = run_command(['ln', '-s' , '/var/cyclozzo/logs/', '/usr/lib/hadoop/pids'])
    if rc != 0:
        print 'Failed to configure DFS, code = %s : %s' % (rc, out)
        sys.exit(-1)
    rc, out = run_command(['ln', '-s' , '/etc/cyclozzo/', '/usr/lib/hadoop/conf'])
    if rc != 0:
        print 'Failed to configure DFS, code = %s : %s' % (rc, out)
        sys.exit(-1)


def get_pid(app_root):
    dp = os.path.join(app_root, 'pidfile')
    if os.path.exists(dp):
        with open(dp, 'r') as f:
            dpid = int(f.readline())
        return dpid

    else:
        return 0


def main():
    """Commandline utility for configuring Cyclozzo Nodes.
    """
    # path to the master configuration file
    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                               'settings.yaml')
    config = ApplicationConfiguration(config_file)
    fabfile.update_roles(config)

    # define commandline options
    usage = 'cyclozzo-lite [options]'
    parser = OptionParser(usage)
    parser.add_option('-e', '--exchange-keys', action='store_true', 
                      default=False,
                      help='Exchange SSH keys between Master and Slaves',
                      dest='exchange_keys')
    parser.add_option('-t', '--settings', action='store_true', default=False,
                      help='Configuration file for Cyclozzo node settings.')
    parser.add_option('-c', '--configure', action='store_true', default=False,
                      help='Configure Cyclozzo Master/Client Services')
    parser.add_option('-f', '--format', default=False, dest='format',
                      help='Format DFS and DS. Options: [dfs, ds, all]',
                      choices=['ds', 'dfs', 'all'])
    parser.add_option('-s', '--start', default=False, dest='start',
                      help='Start Cyclozzo Cluster/Application. ' \
                      'Options: [cluster, application]',
                      choices=['cluster', 'application'])
    parser.add_option('-k', '--stop', default=False, dest='stop',
                      help='Stop Cyclozzo Cluster/Application Services. ' \
                      'Options: [cluster, application]',
                      choices=['cluster', 'application'])
    parser.add_option('--status', default=False, dest='status',
                      help='List Cluster/Application status. ' \
                      'Options: [cluster, application]',
                      choices=['cluster', 'application'])

    parser.add_option('--dir',  help='Application Directory', dest='app_dir')
    parser.add_option('--port', help='Listen port number', type='int')
    parser.add_option('--debug', action='store_true', default=False,
                        help='Run the application in foreground')


    # parse the options
    (options, args) = parser.parse_args()

    if options.exchange_keys:
        fabfile.exchange_keys()

    elif options.settings:
        print config_file

    elif options.configure:
        if not config.slaves:
            config.slaves=[]
        # configure hadoop and hypertable on (this) master
        configure_hadoop(primary=config.master, 
                         secondary=config.slaves)
        configure_hypertable(primary=config.master, 
                             secondary=config.slaves)
        fabfile.rsync()
        if options.format == 'dfs' or options.format == 'all':
            fabfile.start_hadoop_namenode()
            fabfile.start_hadoop_datanode()
            fabfile.format_hadoop_datanode()
            fabfile.format_hadoop_namenode()
            fabfile.stop_hadoop_datanode()
            fabfile.stop_hadoop_namenode()
            print '--> Waiting for Name/Datanode to stop (5 secs)'
            sleep(5)
        if options.format == 'ds' or options.format == 'all':
            fabfile.start_hadoop_namenode()
            fabfile.start_hadoop_datanode()
            fabfile.start_dfsbrokers()
            fabfile.format_hypertable()
            fabfile.stop_hadoop_datanode()
            fabfile.stop_hadoop_namenode()
            print '--> Waiting for Name/Datanode to stop (5 secs)'
            sleep(5)
                    
    elif options.start == 'cluster':
        fabfile.start()

    elif options.stop == 'cluster':
        fabfile.stop()

    elif options.start == 'application':
        if not options.app_dir or not options.port:
            print 'Missing arguments: --app_dir, --port'
            parser.print_help()
        else:
            print 'Starting application from %s on port %d' % \
                            (options.app_dir, options.port)
            appserver_yaml = os.path.join(
                                          os.path.dirname(                                                     
                                                    os.path.abspath(
                                                    appserver.__file__
                                                    )
                                                          ), 
                                          'appserver.yaml')
            appserver_yaml = ApplicationConfiguration(appserver_yaml)
            if options.debug:
                appserver_yaml.debug_mode = True
            daemon = AppDaemon(appserver_yaml, 
                               options.app_dir, 
                               None, 
                               options.port, 
                               None, 
                               None
                               )
            if options.debug:
                daemon.run_application()
            else:
                daemon.start()

    elif options.stop == 'application':
        if not options.app_dir:
            print 'Missing arguments: --app_dir'
            parser.print_help()
        else:
            pid = get_pid(options.app_dir)
            if pid == 0:
                print 'No instance running'
                sys.exit(1)
            print 'Stopping instance with pid %d' % pid
            os.kill(pid, signal.SIGTERM)

    elif options.status == 'application':
        if not options.app_dir:
            print 'Missing arguments: --app_dir'
            parser.print_help()
        pid = get_pid(options.app_dir)
        running = os.path.exists('/proc/%d' %pid)
        if pid and running:
            print 'Application with process id %d is running' %pid
        elif pid:
            print 'Application with process id %d is stopped' %pid
        else:
            print 'Application is not running'
    elif options.status == 'cluster':
        print 'Cluster status not available.'
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
