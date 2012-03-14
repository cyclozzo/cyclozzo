PYTHON						=	`which python`
PROJECT						=	cyclozzo
DATE						=	`date "+%Y-%m-%d"`

# Pakcage Versions
MAJOR						=	"1.0.1"
SDK_MAJOR					=	"1.0.138"
HYPERTABLE_VERSION			=	"0.9.5.0-3cyclozzo1"
HADOOP_VERSION				=	"0.20.2+923.142"
PYTHON_THRIFT_VERSION		=	"0.6.1"
CELERY_VERSION				=	"2.3.3"
PYTHON_DATEUTIL_VERSION		=	"1.5"
PYTHON_AMQPLIB_VERSION		=	"1.0.2"
PYTHON_ANYJSON_VERSION		=	"0.3.1"
PYTHON_IMPORTLIB_VERSION	=	"1.0.2"
PYTHON_KOMBU_VERSION		=	"1.4.1"
PYTHON_ORDEREDDICT_VERSION	=	"1.1"
FABRIC_VERSION				=	"1.2.2"
PYTHON_CRYPTO_VERSION		=	"2.3"
PYTHON_PARAMIKO_VERSION		=	"1.7.7.1"
PYTHON_PYLIBMC_VERSION		=	"1.2.1"
PYTHON_BRUKVA_VERSION		=	"0.0.1"



help:
	@echo "Cyclozzo Build Scripts"
	@echo ""
	@echo "make all - Build all Cyclozzo Packages"
	@echo "make develop - Install Development Environment"


info: 
	@echo "Build Information : $(DATE)"
	@echo "Build version $(MAJOR)"


cyclozzo-appserver:
	@echo "\nBuilding Cyclozzo Appserver Debian Package\n"
	cd $(CURDIR)/../cyclozzo-appserver; debchange -v $(MAJOR) -m; dpkg-buildpackage -i -I -rfakeroot;
	@echo "\nBuild Done\n"


cyclozzo-runtime:
	@echo "\nBuilding Cyclozzo Runtime Debian Package\n"
	cd $(CURDIR)/../cyclozzo-runtime; debchange -v $(MAJOR) -m; dpkg-buildpackage -i -I -rfakeroot;
	@echo "\nBuild Done\n"


cyclozzo-sdk:
	@echo "\nBuilding Cyclozzo SDK Debian Package\n"
	cd $(CURDIR)/../cyclozzo-sdk; debchange -v $(SDK_MAJOR) -m; dpkg-buildpackage -i -I -rfakeroot;
	@echo "\nBuild Done\n"


cyclozzo-ose:
	@echo "\nBuilding Cyclozzo Lite Debian Package\n"
	cd $(CURDIR)/../cyclozzo-ose; debchange -v $(MAJOR) -m; dpkg-buildpackage -i -I -rfakeroot;
	@echo "\nBuild Done\n"


python-thrift:
	@echo "\nBuilding Python-Thrift Debian Package\n"
	cd $(CURDIR)/../python-thrift; debchange -v $(PYTHON_THRIFT_VERSION) -m; dpkg-buildpackage -i -I -rfakeroot;
	@echo "\nBuild Done\n"


fabric:
	@echo "\nBuilding Fabric Debian Package\n"
	cd $(CURDIR)/../deps/fabric; debchange -v $(FABRIC_VERSION) -m; dpkg-buildpackage -i -I -rfakeroot;
	@echo "\nBuild Done\n"


python-crypto:
	@echo "\nBuilding Python-Crypto Debian Package\n"
	cd $(CURDIR)/../deps/pycrypto; debchange -v $(PYTHON_CRYPTO_VERSION) -m; dpkg-buildpackage -i -I -rfakeroot;
	@echo "\nBuild Done\n"
    

python-paramiko:
	@echo "\nBuilding Python-Paramiko Debian Package\n"
	cd $(CURDIR)/../deps/paramiko; debchange -v $(PYTHON_PARAMIKO_VERSION) -m; dpkg-buildpackage -i -I -rfakeroot;
	@echo "\nBuild Done\n"


python-pylibmc:
	@echo "\nBuilding Python-Pylibmc Debian Package\n"
	cd $(CURDIR)/../deps/pylibmc; debchange -v $(PYTHON_PYLIBMC_VERSION) -m; dpkg-buildpackage -i -I -rfakeroot;
	@echo "\nBuild Done\n"


python-brukva:
	@echo "\nBuilding Python-Brukva Debian Package\n"
	cd $(CURDIR)/../deps/brukva; debchange -v $(PYTHON_BRUKVA_VERSION) -m; dpkg-buildpackage -i -I -rfakeroot;
	@echo "\nBuild Done\n"


hadoop:
	@echo "\nBuilding Hadoop Debian Package\n"
	cd $(CURDIR)/../deps/hadoop; debchange -v $(HADOOP_VERSION) -m; dpkg-buildpackage -i -I -rfakeroot;
	@echo "\nBuild Done\n"


hypertable:
	@echo "\nBuilding Hypertable Debian Package\n"
	cd $(CURDIR)/../deps/hypertable; debchange -v $(HYPERTABLE_VERSION) -m; dpkg-buildpackage -i -I -rfakeroot;
	@echo "\nBuild Done\n"


all: cyclozzo-appserver cyclozzo-sdk cyclozzo-runtime cyclozzo-ose python-thrift hadoop hypertable fabric python-crypto python-paramiko python-pylibmc python-brukva
	@echo "\nBuilding All Packages for Cyclozzo OSE\n"


develop:
	@echo "\nSetting up Cyclozzo Development Environment\n"
	cd $(CURDIR)/../python-thrift; sudo python setup.py develop
	cd $(CURDIR)/../cyclozzo-runtime; sudo python setup.py develop
	cd $(CURDIR)/../cyclozzo-sdk; sudo python setup.py develop
	cd $(CURDIR)/../cyclozzo-appserver; sudo python setup.py develop
	cd $(CURDIR)/../cyclozzo-ose; sudo python setup.py develop

