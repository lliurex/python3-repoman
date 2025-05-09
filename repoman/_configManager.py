#/usr/bin/env python3
import os,sys,shutil
import json
try:
	from ._repoFile import _repoFile
except:
	from _repoFile import _repoFile
try:
	from .errorcode import errorEnum
except:
	from errorcode import errorEnum
try:
	from appconfig import appConfigN4d
except:
	appConfigN4d=None

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
		#content={} 
		with open(jFile,"r") as f:
			jcontent=json.loads(f.read())
		cleanFields=["Enabled","changed","disabled_repos"]
		for cleanf in cleanFields:
			for repo,repodata in jcontent.items():
				if cleanf in repodata.keys():
					repodata.pop(cleanf)
		#for key in content.keys():
		#	newkey=key
		#	if key.endswith("/")==False:
		#		newkey+="/"
		#	jcontent[newkey]=content[key]
		return(jcontent)
	#def _readJFile

	def _isMirrorEnabled(self):
		sw=False
		if appConfigN4d!=None:
			sw=True
			n4d=appConfigN4d.appConfigN4d()
			ret=n4d.n4dQuery("MirrorManager","is_mirror_available")
			if isinstance(ret,dict):
				if str(ret.get("status","-1"))!="0":
					sw=False
			elif isinstance(ret,str):
				if ret!="Mirror available":
					sw=False
		return(sw)

	def getRepos(self,default=False):
		sortrepos={}
		if os.path.exists(CONFDIR):
			if default==True:
				dirs=[os.path.join(CONFDIR,"default")]
			else:
				dirs=[os.path.join(CONFDIR,"default"),CONFDIR]
			uris={}
			for dir in dirs:
				repos={}
				for f in os.scandir(dir):
					if f.path.endswith(".json"):
						jRepo=self._readJFile(f.path)
						for key,data in jRepo.items():
							URIs=data.get("repos",[])
							if len(URIs)>0:
								uri=URIs[0].split(" ")[0]
								suite=URIs[0].split(" ")[1]
								if uri not in uris:
									uris.update({uri:suite})
									repos.update({key:data})
				sortkeys=list(repos.keys())
				sortkeys.sort()
				for key in sortkeys:
					sortrepos.update({key:repos[key]})
					sortrepos[key].update({"Name":key})
					uris=repos[key].get("repos",[])
					if len(uris)>0:
						if uris[0].startswith("http://mirror/"):
							sortrepos[key].update({"available":self._isMirrorEnabled()})
		repos=self._getDEB822(sortrepos)
		return(repos)
	#def getRepos

	def _getDEB822(self,repos):
		repos822={}
		for repokey,repodata in repos.items():
			repo822=_repoFile()
			fpath=os.path.join(CONFDIR,"{}.sources".format(repokey[-3]))
			repo822.setFile(fpath.replace(".sources",".list"))
			for repo in repodata.get("repos",[]):
				repo="deb {}\n".format(repo)
				repo822.raw+=repo
			fcontent=repo822.getRepoDEB822()
			repo822.setFile(fpath)
			repo822.raw=fcontent
			fcontent.update({"Name":repokey})
			repos822.update({repokey:fcontent[list(fcontent.keys())[0]]})
			repos822[repokey].update({"Name":repokey})
		return(repos822)
		
#class _configManager
