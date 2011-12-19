import os

#this_dir = os.path.dirname(os.path.abspath(__file__))


with open('MANIFEST.in', 'w') as flist:
	for root, dirs, files in os.walk('./'):
		for f in files:
			f = os.path.join('cyclozzo/lib', root[2:], f)
			if '.svn' in f: continue
			flist.write('include ' + f + '\n')
		
