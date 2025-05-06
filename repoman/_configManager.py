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

	def getRepos(self):
		repos={}
		if os.path.exists(CONFDIR):
			for f in os.scandir(CONFDIR):
				if f.path.endswith(".json"):
					repos.update(self._readJFile(f.path))
		return(repos)
	#def getRepos

