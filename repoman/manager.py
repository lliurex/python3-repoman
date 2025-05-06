#/usr/bin/env python3
import os,sys,shutil
import yaml
from ._repoFile import _repoFile
from ._configManager import _configManager
from ._repoScrapper import _repoScrapper

BASEDIR="/etc/apt"
OLDLIST=os.path.join(BASEDIR,"sources.list")
SOURCESDIR=os.path.join(BASEDIR,"sources.list.d")
TRUSTEDDIR=os.path.join(BASEDIR,"trusted.gpg.d")

class manager():
	def __init__(self):
		self.dbg=True
	#def __init__

	def _debug(self,msg):
		if self.dbg==True:
			print("manager: {}".format(msg))
	#def _debug
	
	def getRepos(self):
		repos={}
		if os.path.exists(OLDLIST):
			repo=_repoFile()
			repo.setFile(OLDLIST)
			repos.update(repo.getRepoDEB822())
		for f in os.scandir(SOURCESDIR):
			repo=_repoFile()
			repo.setFile(f.path)
			repos.update(repo.getRepoDEB822())
		return(repos)
	#def getRepos

	def _getReposByState(self,state=True):
		configuredRepos=self.getRepos()
		repos={}
		for repo in configuredRepos:
			for frepo,fdata in repo.items():
				for uri,data in fdata.items():
					if data.get("Enabled",True)==state:
						repos[uri]=data
		return(repos)
	#def _getReposByState

	def _getManagedRepos(self):
		managedRepos=_configManager()
		return(managedRepos.getRepos())
	#def _getManagedRepos

	def getEnabledRepos(self):
		return(self._getReposByState(True))
	#def getEnabledRepos

	def getDisabledRepos(self):
		return(self._getReposByState(False))
	#def getDisabledRepos

	def getRepoByName(self,name):
		repos=self.getRepos()
		repo={}
		uri=""
		for repouri,data in repos.items():
			if data["Name"]==name:
				uri=repouri
		if uri!="":
			repo=repos[uri]
		return(repo)
	#def getRepoByName

	def getRepoByUri(self,uri):
		repos=self.getRepos()
		repo={}
		for repouri,data in repos.items():
			if data["URIs"]==uri:
				break
			repouri=""
		if repouri!="":
			repo=repos[uri]
		return(repo)
	#def _getRepoByUri

	def enableRepoByName(self,name):
		repo=self.getRepoByName(name)
		if len(repo)>0:
			repo["Enabled"]=True
		self._writeRepo(repo)
		return(repo)
	#def enableRepoByName

	def disableRepoByName(self,name):
		repo=self.getRepoByName(name)
		if len(repo)>0:
			repo["Enabled"]=False
		self._writeRepo(repo)
		return(repo)
	#def enableRepoByName

	def addRepo(self,url,name="",desc=""):
		uri=url.replace("deb ","").strip()
		if len(self.getRepoByUri(uri))>0:
			print("Already present")
		else:
			scrapper=_repoScrapper()
			scrapper.addRepo(uri)
	#def addRepo

	def _writeRepo(self,repo):
		fname=repo.get("file")
		if len(fname)>0:
			frepo=_repoFile()
			frepo.writeFromData(repo)
	#def _writeRepo

	def _generateConfigFromSources(self):
		repos=self.getRepos()
		managedRepos=self._getManagedRepos()
		rawRepos={}
		for repo in repos:
			for fRepo,fData in repo.items():
				rawRepos.update(fData)
		for repoUri in rawRepos.keys():
			if repoUri in managedRepos:
				pass
			else:
				managedRepos.update({repoUri:rawRepos[repoUri]})
		print(managedRepos)
	#def _generateConfigFromSources

	def _generateSourcesFromConfig(self):
		repos=self.getRepos()
		managedRepos=self._getManagedRepos()
		rawRepos={}
		for repo in repos:
			for fRepo,fData in repo.items():
				rawRepos.update(fData)
		for repoUri in managedRepos.keys():
			rawRepos.update({repoUri:managedRepos[repoUri]})
		print(rawRepos)
	#def _generateSourcesFromConfig
#class manager
