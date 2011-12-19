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
# Cyclozzo Build Routines module for packaging
# @author: Stanislav Yudin


import os, sys, datetime, shutil, logging
from cyclozzo.runtime.lib.cmnd import run_command
log = logging.getLogger(__name__)

class BuildException(Exception):
	pass
	
class ExecutionException(Exception):
	pass
	
def build_egg(target, release, deps):
	dist = os.path.join(target, 'dist')
	if os.path.exists(dist):
		shutil.rmtree(dist)
	
	rc = run_command(['python', os.path.join(target, 'setup.py'), 'bdist_egg'], log = log)	
	if rc[0] != 0:
		raise ExecutionException('bdist_egg failed: code %d, %s' % rc)
	
	log.debug('dist: %s' % dist)
	files = os.listdir(dist)
	files = filter(
		lambda x : x.endswith('.egg'),
		files)
	if len(files) > 1:
		raise BuildException('Yarr! There is more than one egg after build:\n%s' % '\n'.join(files))
	
	egg = os.path.join(dist, files[0])
	log.debug(' ## %s build info : %s ## ' % (target, datetime.datetime.now()) )
	log.debug('egg: %s' % egg)
	log.debug('release: %s' % release)
	log.debug('deps: %s' % deps)
	ez_setup = os.path.join(target, 'ez_setup.py')
	ez_setup_cmd = ['python', ez_setup, '-zmaxd', deps, '-f', release, egg]

	rc = run_command(command = ez_setup_cmd, log = log)	
	if rc[0] != 0:
		raise ExecutionException('"%s" failed: %s' % (' '.join(ez_setup_cmd), rc[1]) )
	
	rc = run_command(['cp', '-f', os.path.join(deps, '*'), release], log = log)
	if rc[0] !=0:
		raise ExecutionException('move to release folder failed: %s' % rc[1] )

	files = os.listdir(release)
	log.debug('built to %s' % release)
	for f in files: log.debug(' ->', f)
	return files
	
def prepare_release_folder(target):
	release = os.path.join(target, 'release')
	if os.path.exists(release):
		log.debug('removing release folder')
		shutil.rmtree(release)
		
	os.makedirs(release)
	
	return release

class DependecyException(Exception):
	pass
	
def check_deps(target, deps_list):
	deps = os.path.join(target, 'deps')
	if not os.path.exists(deps):
		log.debug('No dependeces specified!')
		os.makedirs(deps)
	
	found = []
	def is_not_dotfile(line):
		if line and line[0] != '.':
			return True
		else:
			return False
			
	all_files = filter(is_not_dotfile, os.listdir(deps))
	if len(all_files) != len(deps_list):
		raise DependecyException('Wrong files found in deps folder.\nFound:%s\nRequired:%s' %
			( ', '.join(all_files), ', '.join(deps_list) ) )
	
	for f in all_files:
		log.debug('checking file %s' % f)
		for dep_name in deps_list: 
			if dep_name in f and not dep_name in found:
				found.append(dep_name)
				log.debug('found %s' % dep_name)

	not_found = None
	for dep in deps_list:
		if not dep in found:
			not_found = dep
			break
	
	if not not_found:
		return deps
	else:
		raise DependecyException('''
Additional packages reqired to be added to 
%s
Found:%s
Reqired:%s
Missed: %s
''' % (deps, found, deps_list, not_found))

def pack_eggs(release, name, version):
	tar_cmd = 'tar -c %s >> %s' % (release, '%s_%s.tar' % (name, version))
	if os.system(tar_cmd) != 0:
		raise ExecutionException('%s - failed with nonzero' % tar_cmd)

	tarball = '%s_%s.tar.bz2' % (name, version)
	if os.path.exists(tarball):
		os.remove(tarball)

	bzip2_cmd = 'bzip2 %s_%s.tar' % (name, version)
	if os.system(bzip2_cmd) != 0:
		raise ExecutionException('%s - failed with nonzero' % bzip2_cmd)
	
	log.debug('built tarball: %s' % tarball)
	os.system('rm -r %s' % release)
	return tarball

def create_virtual_env(target, release, package_name, version, restricted = False):
	package_dir = os.path.join(target, '%s_tmp' %package_name)
	if os.path.exists(package_dir):
		shutil.rmtree(package_dir)
	
	# Create a virtual python environment
	if restricted:
		virtual_env_cmd = 'virtualenv --no-site-packages %s' %package_dir
	else:
		virtual_env_cmd = 'virtualenv %s' %package_dir
	log.debug('Creating virtual python environment: %s' %virtual_env_cmd)
	os.system(virtual_env_cmd)
	
	# Install the eggs from release directory
	easy_install = os.path.join(package_dir, 'bin/easy_install')
	sdk_egg = os.listdir((os.path.join(target, 'dist')))[0]
	os.system('%s -H None -f %s %s' %(easy_install, release, os.path.join(release, sdk_egg)))
		
	# Package the sdk
	tar_cmd = 'tar -c %s >> %s' % (package_dir, '%s_%s.tar' % (package_name, version))
	if os.system(tar_cmd) != 0:
		raise ExecutionException('%s - failed with nonzero' % tar_cmd)

	tarball = '%s_%s.tar.bz2' % (package_name, version)
	if os.path.exists(tarball):
		os.remove(tarball)
		
	bzip2_cmd = 'bzip2 %s_%s.tar' % (package_name, version)
	if os.system(bzip2_cmd) != 0:
		raise ExecutionException('%s - failed with nonzero' % bzip2_cmd)
	
	log.debug('built tarball: %s' % tarball)
	