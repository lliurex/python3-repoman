#/usr/bin/env python3
import os,sys,shutil
import json

CONFDIR="/usr/share/repoman/sources.d"

class _configManager():
	def __init__(self):
		self.dbg=True
	#def __init__

	def _debug(self,msg):
		if self.dbg==True:
			print("_configManager: {}".format(msg))
	#def _debug

	def _readJFile(self,jFile):
		jcontent={} 
		content={} 
		with open(jFile,"r") as f:
			content=json.loads(f.read())
		for key in content.keys():
			newkey=key
			if key.endswith("/")==False:
				newkey+="/"
			jcontent[newkey]=content[key]
		return(jcontent)
	#def _readJFile

	def getRepos(self,default=False):
		sortRepos={}
		if os.path.exists(CONFDIR):
			if default==True:
				dirs=[os.path.join(CONFDIR,"default")]
			else:
				dirs=[os.path.join(CONFDIR,"default"),CONFDIR]
			for dir in dirs:
				repos={}
				for f in os.scandir(dir):
					if f.path.endswith(".json"):
						repos.update(self._readJFile(f.path))
				sortkeys=list(repos.keys())
				sortkeys.sort()
				for key in sortkeys:
					sortRepos.update({key:repos[key]})
		return(sortRepos)
	#def getRepos
#class _configManager
