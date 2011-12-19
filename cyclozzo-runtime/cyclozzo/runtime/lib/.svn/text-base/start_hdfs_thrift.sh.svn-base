#!/bin/sh

TOP=/usr/lib/hadoop
CLASSPATH=$TOP/conf


# the hadoop libraries
for f in $TOP/*.jar ; do
  CLASSPATH=$CLASSPATH:$f
done

# the apache libraries
for f in $TOP/lib/*.jar ; do
  CLASSPATH=$CLASSPATH:$f
done

# the thrift server
for f in $TOP/contrib/thriftfs/*.jar ; do
  CLASSPATH=$CLASSPATH:$f
done
# the thrift hadoop api
for f in ./hdfsthriftlib/*.jar ; do
  CLASSPATH=$CLASSPATH:$f
done

java -Dcom.sun.management.jmxremote -cp $CLASSPATH org.apache.hadoop.thriftfs.HadoopThriftServer $*
