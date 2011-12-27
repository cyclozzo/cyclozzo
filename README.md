## Cyclozzo OSE

Cyclozzo is a meta cloud platform designed to support the latest PaaS APIs with minimal effort. Adding support for new APIs in Cyclozzo is trivial. Currently, Cyclozzo is capable of running Google App Engine compatible applications on its cluster.

Cyclozzo OSE is the opensource version of Cyclozzo providing minimal features.

For more information about Cyclozzo, please visit http://gostackless.com/cyclozzo.html

## Building Cyclozzo

Cyclozzo's build system can build `deb` packages from the sources. Once you have all the dependencies ready in the `deps` directory, do 

    cd buildbot
    make all

and publish the debian repository,

    make publish

Now you'll have an `apt` repository with all the packages and dependencies under `repo` directory.

    ls ../repo
    i386    all     x86_64

You have to add the `repo` directory to have FTP access so that `apt` can access the packages.

## Deploying Cyclozzo

Once the repository is ready, you can add the repository url to all the cluster nodes and install Cyclozzo

    sudo add-apt-repository 'deb ftp://<REPOSITORY-ADDRESS-HERE>/all  /'
    sudo add-apt-repository 'deb ftp://<REPOSITORY-ADDRESS-HERE>/x86_64  /'
    sudo apt-get update
    sudo apt-get install cyclozzo-ose

NOTE: You may need to enter a password for SSH keys generated during installation. Leave it empty for passwordless SSH access.

## Configuring Cyclozzo cluster

First of all you need to select a master node. This is the node from where you control all the other nodes and run commands. Once you are on the master node, issue

    sudo nano `cyclozzo --settings`

and change the master and slave node ip addresses. Then do,

    cyclozzo --exchange-keys

to exchange the SSH keys generated during installation to all the slave nodes.

Now, its time to configure/format the cluster

    cyclozzo --configure --format all

## Starting Cyclozzo cluster

    cyclozzo --start cluster

## Starting applications

    cyclozzo --start application --dir guestbook/ --port 8080

## About Stackless Recursion

Please visit http://gostackless.com/