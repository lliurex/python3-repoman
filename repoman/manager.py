#/usr/bin/env python3
import os,sys,shutil
import subprocess
import yaml
try:
	from ._repoFile import _repoFile
except:
	from _repoFile import _repoFile
try:
	from ._configManager import _configManager
except:
	from _configManager import _configManager
try:
	from ._repoScrapper import _repoScrapper
except:
	from _repoScrapper import _repoScrapper

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

	def updateRepos(self):
		cmd=["apt","update"]
		try:
			subprocess.run(cmd)
		except Exception as e:
			print("ERROR: {}".format(e))
	#def updateRepos
	
	def getRepos(self,sorted=False):
		repos={}
		if os.path.exists(OLDLIST):
			repo=_repoFile()
			repo.setFile(OLDLIST)
			repos.update(repo.getRepoDEB822())
		for f in os.scandir(SOURCESDIR):
			repo=_repoFile()
			repo.setFile(f.path)
			repos.update(repo.getRepoDEB822())
		if sorted==True:
			repos=self._sortRepos(repos)
		return(repos)
	#def getRepos

	def _sortRepos(self,repos):
		mRepos=_configManager()
		sortedRepos={}
		for name,data in mRepos.getRepos().items():
			sortedRepos.update({name:data})
			repo=self.getRepoByName(name,repos)
			if len(repo)>0:
				repos.pop(repo["URIs"])
		sortedRepos.update(repos)
		return(sortedRepos)
	#def _sortRepos

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

	def _getManagedRepos(self,default=False):
		managedRepos=_configManager()
		return(managedRepos.getRepos(default))
	#def _getManagedRepos

	def getEnabledRepos(self):
		return(self._getReposByState(True))
	#def getEnabledRepos

	def getDisabledRepos(self):
		return(self._getReposByState(False))
	#def getDisabledRepos

	def getRepoByName(self,name,repos={}):
		if len(repos)==0:
			repos=self.getRepos()
		repo={}
		uri=""
		for repouri,data in repos.items():
			if data["Name"]==name:
				uri=repouri
				break
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
		return(self._writeRepo(repo))
	#def enableRepoByName

	def disableRepoByName(self,name):
		repo=self.getRepoByName(name)
		if len(repo)>0:
			repo["Enabled"]=False
		return(self._writeRepo(repo))
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
		retVal=1
		fname=repo.get("file")
		if len(fname)>0:
			frepo=_repoFile()
			frepo.writeFromData(repo)
			retVal=0
		return(retVal)
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
	#def _generateSourcesFromConfig
#class manager
