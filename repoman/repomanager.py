#/usr/bin/env python3
import os,sys,shutil
import subprocess
import yaml
try:
	from .errorcode import errorEnum
except:
	from errorcode import errorEnum
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
		try:
			release=subprocess.check_output(["lliurex-version","-n"],encoding="utf8").strip().replace("\t"," ")
			release=release.split(".")[0]
		except:
			release=25
		self.llxRelease=release
	#def __init__

	def _debug(self,msg):
		if self.dbg==True:
			print("manager: {}".format(msg))
	#def _debug

	def updateRepos(self):
		error=errorEnum(0)
		cmd=["apt","update"]
		try:
			subprocess.run(cmd)
		except Exception as e:
			error=errorEnum(6)
		return(error)

	#def updateRepos
	
	def getRepos(self,includeAll=False):
		repos={}
		if os.path.exists(OLDLIST):
			repo=_repoFile()
			repo.setFile(OLDLIST)
			repos.update(repo.getRepoDEB822())
		for f in os.scandir(SOURCESDIR):
			repo=_repoFile()
			repo.setFile(f.path)
			repos.update(repo.getRepoDEB822())
		if includeAll==True:
			repos=self._getAllRepos(repos)
		return(repos)
	#def getRepos

	def _getAllRepos(self,repos):
		mRepos=self._getManagedRepos()
		sortedRepos={}
		uri=""
		for name,data in mRepos.items():
			repo=self.getRepoByUri(data["URIs"],repos)
			if len(repo)>0:
				if data["Suites"] == repo.get("Suites"):
					#Same uri and same suite. Duplicated
					if repo["URIs"] in repos.keys():
						repos.pop(repo["URIs"])
					if repo["Name"] in repos.keys():
						repos.pop(repo["Name"])
				data["Enabled"]=repo["Enabled"]
				data["file"]=repo["file"]
			popkey=repo.get("URIs","")
			repo=self.getRepoByName(data["URIs"],repos)
			if len(repo)<=0:
				repo=self.getRepoByName(name,repos)
				popkey=repo.get("Name","")
			if len(repo)>0:
				data["Enabled"]=repo["Enabled"]
				if os.path.exists(data["file"])==False:
					data["Enabled"]=False
				if popkey in repos.keys():
					repos.pop(popkey)
			else:
				data["Enabled"]=False
			data["file"]=repo.get("file",data["file"])
			sortedRepos.update({name:data})
		sortedRepos.update(repos)
		return(sortedRepos)
	#def _sortRepos

	def _getManagedRepos(self):
		mRepos=_configManager()
		return(mRepos.getRepos())
	#def _getManagedRepos(self):

	def _getReposByState(self,state=True):
		configuredRepos=self.getRepos()
		repos={}
		for uri,repo in configuredRepos.items():
			if repo.get("Enabled",True)==state:
				repos[uri]=repo
		return(repos)
	#def _getReposByState

	def getRepoByName(self,name,repos={}):
		mrepos={}
		repo={}
		if len(repos)==0:
			repos=self.getRepos()
			repos.update(self._getManagedRepos())
		for repokey,repodata in repos.items():
			if repokey.lower()==name.lower():
				repo=repos[repokey].copy()
				break
			elif repodata["Name"].lower()==name.lower():
				repo=repos[repokey].copy()
				break
		return(repo)
	#def getRepoByName

	def getRepoByUri(self,uri,repos={}):
		mrepos={}
		repo={}
		if len(repos)==0:
			repos=self.getRepos()
			repos.update(self._getManagedRepos())
		for repokey,repodata in repos.items():
			if repodata.get("URIs").rstrip("/")==uri.rstrip("/"):
				repo=repos[repokey].copy()
				break
		return(repo)
	#def _getRepoByUri

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

	def enableRepoByName(self,name):
		repo=self.getRepoByName(name)
		if len(repo)<=0:
			repo=self.getRepoByName("{}.sources".format(name))
		if len(repo)<=0:
			repo=self.getRepoByName("{}.list".format(name))
		if len(repo)>0:
			repo["Enabled"]=True
		return(self._writeRepo(repo))
	#def enableRepoByName

	def enableDefault(self):
		repos=self._getManagedRepos(default=True)
		for uri,repo in repos.items():
			if "lliurex" in uri.lower() and "mirror" not in uri.lower():
				self.enableRepoByName(repo["Name"])
	#def enableDefault

	def disableRepoByName(self,name):
		repo=self.getRepoByName(name)
		if len(repo)<=0:
			repo=self.getRepoByName("{}.sources".format(name))
		if len(repo)<=0:
			repo=self.getRepoByName("{}.list".format(name))
		if len(repo)>0:
			repo["Enabled"]=False
		return(self._writeRepo(repo))
	#def enableRepoByName

	def disableAll(self):
		repos=self.getEnabledRepos()
		for uri,repo in repos.items():
			repo["Enabled"]=False
			self._writeRepo(repo)
	#def disableAll(self):

	def addRepo(self,url,name="",desc="",signedby=""):
		error=errorEnum.NO_ERROR
		uri=url.replace("deb ","").strip()
		if len(self.getRepoByUri(uri))>0:
			error=errorEnum.ALREADY_PRESENT
		else:
			scrapper=_repoScrapper()
			error=scrapper.addRepo(uri,name,desc,signedby)
		return(error)
	#def addRepo

	def _writeRepo(self,repo):
		error=errorEnum(0)
		fname=None
		if repo!=None:
			fname=repo.get("file")
		if fname!=None:
			if os.path.exists(os.path.join(SOURCESDIR,os.path.basename(fname)))==True:
				fname=os.path.join(SOURCESDIR,os.path.basename(fname))
				repo["file"]=fname
			if os.path.basename(fname)=="lliurex_{}.sources".format(self.llxRelease):
				if os.path.exists(fname):
					os.unlink(fname)
				fname=fname.replace("_{}".format(self.llxRelease),"")
				repo["file"]=fname
			if len(fname)>0:
				frepo=_repoFile()
				frepo.writeFromData(repo)
		else:
			error=errorEnum.NOT_FOUND
		return(error)
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

	def chkPinning(self,pinfile=""):
		pin=False
		fcontent=""
		if len(pinfile)<=0:
			pinfile="/etc/apt/preferences.d/lliurex-pinning"
		if os.path.exists(pinfile):
			with open(pinfile,"r") as f:
				fcontent=f.read()
		keys=["Package","Pin","Pin-Priority"]
		for line in fcontent.split("\n"):
			if line.strip().startswith("#")==True or ":" in line.strip()==False:
				continue
			spl=line.split(":")
			if line.split(":")[0] in keys:
				keys.remove(line.split(":")[0])
		if len(keys)==0:
			pin=True
		return(pin)
	#def chkPinning

	def reversePinning(self,pinfile=""):
		error=errorEnum(0)
		fcontent=""
		keys=["Package","Pin","Pin-Priority"]
		if len(pinfile)<=0:
			pinfile="/etc/apt/preferences.d/lliurex-pinning"
		sfile=pinfile
		if os.path.exists(sfile)==False:
			sfile="/usr/share/first-aid-kit/rsrc/lliurex-pinning"
			keys=[]
		if os.path.exists(sfile):
			with open(sfile,"r") as f:
				fcontent=f.read()
		else:
			error
		content=[]
		for line in fcontent.split("\n"):
			raw=line.strip()
			if ":" in line:
				raw=line.replace("#","")
				if raw.strip().split(":")[0] in keys:
					if line.strip()[0]=="P":
						raw="#{}".format(raw)
			if len(raw)>0:
				content.append("{}\n".format(raw))
		if len(content)>0:
			with open(pinfile,"w") as f:
				f.writelines(content)
	#def reversePinning
#class manager
