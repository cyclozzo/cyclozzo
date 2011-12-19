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
import sys
from optparse import OptionParser
import os
import urllib2
import re
import urllib, urlparse, fnmatch, htmllib, formatter
import time
import logging

urlopen = urllib2.urlopen
log = logging.getLogger(__name__)

def downloadFile(path, base_path, filename, local_path):
	originalFileName = filename
	filename = filename.replace("%20", " ")
	originalPath = path
	if path.startswith("https"): path = path[8:]
	elif path.startswith("http://"): path = path[7:]
	elif path.startswith("ftp://"): path = path[6:]
	elif path.startswith("file://"): path = path[7:]

	queryPath = originalPath
	if queryPath.endswith("/"):
		queryPath += originalFileName
	try:
		counter = 1
		max_count = 12
		while True:
			try:
				remoteFile = urlopen(queryPath)
				break
			except urllib2.URLError, e:
				if counter >= max_count:
					raise
				log.debug('Got an error: %s' % e)
				log.debug('Sleeping for 5 sec..')
				time.sleep(5)
				counter += 1
	except Exception, ex:
		#Handle failed files here
		log.error('Error downloading file:' + filename + "<===>" + str(ex))
		return False
	
	#local path
	log.debug("base path: " + base_path)
	local_path = os.path.join(local_path, path[path.find(base_path) + len(base_path):path.find(originalFileName)])
	log.debug("local path:" + local_path)
	if len(local_path) > 0 and (not os.path.exists(local_path)):
		os.makedirs(local_path)
	
	localFile = open(local_path + filename, "wb")
	log.debug("Getting (" + filename + ")")
	fetched = 0
	try:
		while True:
			buf = remoteFile.read(4096)
			rlen = len(buf)
			if rlen == 0:	# EOF reached
				log.debug("Retrieved %d bytes - complete" %fetched)
				break

			localFile.write(buf)
			fetched += rlen
	finally:
		localFile.close()
		remoteFile.close()
		
	return True

class HTMLParser:
	def __init__(self):
		self.parser = htmllib.HTMLParser(formatter.NullFormatter())
	def feed(self, msg):
		self.parser.feed(msg)
	def close(self):
		self.parser.close()
	def get_files(self):
		return self.parser.anchorlist

class FTPParser:
	def __init__(self):
		self.files = []
	def feed(self, msg):
		for l in msg.split('\n'):
			m = re.match('^([d-])([-rwxtsS]{9})(\s+\S+){7}\s+(.*)$', l)
			if m == None:
				continue
			gr = m.groups()
			file = gr[3].strip()
			if gr[0] == 'd':
				file = file + '/'
			self.files.append(file)
	def close(self):
		pass
	def get_files(self):
		return self.files 

def getFileList(thePath, noList, depth, base_path, local_path):
	#parser = htmllib.HTMLParser(formatter.NullFormatter())
	parser = None
	if (thePath.startswith("https") or 
		thePath.startswith("http://")):
		parser = HTMLParser()
	elif thePath.startswith("ftp://"):
		parser = FTPParser()
	elif thePath.startswith("file://"):
		parser = HTMLParser()
	counter = 1
	max_count = 12
	while True:
		try:
			f = urlopen(thePath)
			parser.feed(f.read())
			f.close()
			break
		except urllib2.URLError, e:
			if counter >= max_count:
				log.error('Error accessing path: ' + thePath + "<===>" + 
							str(ex))
				raise
			log.debug('Got an error: %s' %e)
			log.debug('Sleeping for 5 sec..')
			time.sleep(5)
			counter += 1

	parser.close()
	for ref in parser.get_files():
		#skip masked
		ok = True
		for i in noList:
			if ref.find(i) > -1:
				ok = False
				break
		if not ok:
			continue
		#skip parent
		if len(thePath) > len(urlparse.urljoin(thePath, ref)):
			continue
		if ref.endswith("/"):
			#this is a directory
			getFileList(urlparse.urljoin(thePath, ref), noList, depth + 1, 
						base_path, local_path)	
		else:
			success = downloadFile(urlparse.urljoin(thePath, ref),
					base_path,
					ref[ref.rfind("/")+1:len(ref)], local_path)
			if success:
				#do something here
				log.debug("Downloaded file: " + urlparse.urljoin(thePath, ref))
			else:
				log.debug("failed to download" + 
							urlparse.urljoin(thePath, ref))
				return False

	return True

def initiate_download(url, local_path='/var/cyclozzo_sys', nogoList=[';','?','=']):
	currentPath = url

	if currentPath.startswith("https"):
		base_path = currentPath[8:]
	elif currentPath.startswith("http://"):
		base_path = currentPath[7:]
	elif currentPath.startswith("ftp://"):
		base_path = currentPath[6:]
	elif currentPath.startswith("file://"):
		base_path = currentPath[7:]
	elif currentPath.startswith('rsync://'):
		proxy = os.getenv('http_proxy')
		if proxy:
			proxy = proxy.replace('http://', '')
			os.putenv('RSYNC_PROXY', proxy)
		os.execvp('rsync', ['rsync', '-avz', currentPath, '.'])

	try:
		try:
			depth = 0
			if currentPath.endswith("/"):
				if not getFileList(currentPath, nogoList, depth, base_path, 
									local_path):
					return 1
			else:
				filename = currentPath[currentPath.rfind("/") + 1 : \
										len(currentPath)]
				if not downloadFile(currentPath, base_path, filename, 
									local_path):
				    return 1    
		finally:
			pass
	except KeyboardInterrupt:
		pass
	return 0

def main():
	parser = OptionParser()
	parser.add_option("-x", dest="noList", help="a comma-separated list of "
						"words that should be avoided", default=";,?,=")
	parser.add_option("-m", dest="url", help="The base url. This will "
					  "download all the files")
	(options, args) = parser.parse_args()

	if options.noList != None:
		nogoList = options.noList.split(',')
	else:
		nogoList = ";,?,=".split(',')
	if options.url == None:
		parser.print_help()
		sys.exit(1)
	elif options.url != None:
		url = options.url
	else:
		parser.print_help()
		sys.exit(1)
	
	initiate_download(url, nogoList)

if __name__ == "__main__":
	sys.exit(main())
