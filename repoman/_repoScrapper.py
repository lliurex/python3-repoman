#/usr/bin/env python3
import os,shutil
import tempfile
try:
	from .errorcode import errorEnum
except:
	from errorcode import errorEnum
try:
	from ._repoFile import _repoFile
except:
	from _repoFile import _repoFile
import requests
import subprocess
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from bs4 import BeautifulSoup

BASEDIR="/etc/apt"
SOURCESDIR=os.path.join(BASEDIR,"sources.list.d")
TRUSTEDDIR=os.path.join(BASEDIR,"trusted.gpg.d")

class _repoScrapper():
	def __init__(self):
		self.dbg=False
	#def __init__

	def _debug(self,msg):
		if self.dbg==True:
			print("Scrapper: {}".format(msg))
	#def _debug

	def _requestSession(self):
		session=requests.Session()
		retry=Retry(connect=3, backoff_factor=0.5)
		adapter=HTTPAdapter(max_retries=retry,pool_block=True)
		session.mount('http://',adapter)
		session.mount('https:',adapter)
		return session
	#def _requestSession

	def _readServerDir(self,session,url):
		dirlist=[]
		req=None
		try:
			self._debug("Accesing {}".format(url))
			host=url.split(":/")[-1]
			host=host.split("/")[1]
			req=session.get("{}/".format(url), verify=True,timeout=5,headers = {'Host':"{}".format(host)})
			self._debug("Connected")
		except Exception as e:
			self._debug("Error connecting to {}: {}".format(url,e))
			error=errorEnum.CONNECTION_FAIL
			error.message=("{}".format(e))
			return(dirlist)
		try:
			content=req.text
			soup=BeautifulSoup(content,'html.parser')
		except Exception as e:
			self._debug("Couldn't open {}: {}".format(url,e))
			return(dirlist)
		links=soup.find_all('a')
		for link in links:
			fname=link.extract().get_text()
			if fname.startswith("."):
				continue
			dirlist.append(fname)
			self._debug("Append {}".format(fname))
		self._debug("DIR: {}".format(dirlist))
		return(dirlist)
	#def _readServerDir

	def _releaseScrap(self,session,url):
		knowedComponents=['main','universe','multiverse','contrib','non-free','restricted','oss','non-oss','partner','preschool']
		components=[]
		self._debug("Release Reading {}".format(url))
		releaseDirs=self._readServerDir(session,url)
		if len(releaseDirs)==0: #Server doesn't list nothing so...
			for component in knowedComponents:
				fcomponent=os.path.join(url.rstrip("/"),component,"binary-amd64","Packages")
				try:
					fcontent=requests.get(fcomponent)
				except:
					continue
				if fcontent.ok==True:
					components.append(component)
		else:
			for component in releaseDirs:
				component=component.replace('/','').lstrip()
				self._debug("Inspect releasedir {}".format(component))
				if component in knowedComponents:
					components.append(component)
		return(components)
	#def _releaseScrap

	def _repositoryScrap(self,session,url):
		repoUrl=[]
		repoData={"name":"","desc":"","orig":"","sign":"","arch":"","vers":""}
		cmd=["lsb_release","-c"]
		output=subprocess.check_output(cmd,encoding="utf8").strip().replace("\t"," ")
		codename=output.split(" ")[-1]
		knowedReleases=[codename,"{0}-updates".format(codename),"{0}-security".format(codename),"stable","unstable"]
		lastChance=url.rstrip("/").split("/")[-1]
		lastChanceReleases=[lastChance,"{0}-updates".format(lastChance),"{0}-security".format(lastChance)]
		self._debug("Repo Reading {}".format(url))
		dirlist=self._readServerDir(session,url)
		if len(dirlist)==0:
			for release in knowedReleases:
				deburl="{}/dists/{}".format(url.rstrip("/"),release)
				components=self._releaseScrap(session,deburl)
				if len(components)>0:
					repoUrl.append("deb {0} {1} {2}".format(url,release," ".join(components)))
		else:
			if "conf/" not in dirlist:
				self._debug("conf not found")
				repoUrl=self._scrapDistribution(url,dirlist)
			else:
				repoUrl,repoData=self._scrapConf(session,url,dirlist)
			if len(repoUrl)==0:
			#There're files but no one seems from a standard repo.
			#Let's honor user desires and give the repo a chance to be added
				components=["noble-cran40"]
				for component in components:
					fcomponent=os.path.join(url.rstrip("/"),component,"Packages")
					try:
						fcontent=requests.get(fcomponent)
					except:
						continue
				if fcontent.ok==True:
					components.append(component)
		if repoData["name"]!="":
			repoData["name"]=repoData["name"]+repoData["vers"].split(".")[0]
		return (repoUrl,repoData)
	#def _repositoryScrap

	def _scrapConf(self,session,url,dirlist):
		repoUrl=[]
		repoData={"name":"","desc":"","orig":"","sign":"","arch":"","vers":""}
		urlconf=os.path.join(url,"conf/")
		dirlist=self._readServerDir(session,urlconf)
		if "distributions" in dirlist:
			fdist=os.path.join(urlconf,"distributions")
			dcontent=requests.get(fdist)
			if dcontent.ok==True:
				fcontent=dcontent.content.decode()
				repoinfo={"codename":"","components":"","description":"","label":""}
				for fline in fcontent.split("\n"):
					if fline.lower().startswith("codename:"):
						if repoinfo.get("codename","")!="":
							repoUrl.append("deb {0} {1} {2}".format(url,repoinfo["codename"],repoinfo["components"]))
						repoinfo={"codename":fline.split(":")[-1].strip(),"components":"","description":"","label":""}
					elif fline.lower().startswith("components:"):
						repoinfo["components"]=fline.split(":")[-1].strip()
					elif fline.lower().startswith("label:") and repoData["name"]=="":
						repoData["name"]=fline.split(":")[-1].strip()
					elif fline.lower().startswith("description:") and repoData["desc"]=="":
						repoData["desc"]=fline.split(":")[-1].strip()
					elif fline.lower().startswith("origin:") and repoData["orig"]=="":
						repoData["orig"]=fline.split(":")[-1].strip()
					elif fline.lower().startswith("signwith:") and repoData["sign"]=="":
						repoData["sign"]=fline.split(":")[-1].strip()
					elif fline.lower().startswith("architectures:") and repoData["arch"]=="":
						repoData["arch"]=fline.split(":")[-1].strip()
					elif fline.lower().startswith("version:") and repoData["vers"]=="":
						repoData["vers"]=fline.split(":")[-1].strip()
				if repoinfo["codename"]!="":
					repoUrl.append("deb {0} {1} {2}".format(url,repoinfo["codename"],repoinfo["components"]))
		return (repoUrl,repoData)
	#def _scrapConf

	def _scrapDistribution(self,url,dirlist):
		repoUrl=[]
		cmd=["lsb_release","-c"]
		output=subprocess.check_output(cmd,encoding="utf8").strip().replace("\t"," ")
		codename=output.split(" ")[-1]
		knowedReleases=[codename,"{0}-updates".format(codename),"{0}-security".format(codename),"stable","unstable"]
		lastChance=url.rstrip("/").split("/")[-1]
		lastChanceReleases=[lastChance,"{0}-updates".format(lastChance),"{0}-security".format(lastChance)]
		if "dists/" in dirlist:
			url=os.path.join(url,"dists/")
		elif "/dists" not in url:
			self._debug("dists not found")
			return(repoUrl)
		dirlist=self._readServerDir(session,url)
		if url.endswith('/dists/'):
			for repodir in dirlist:
				signedby=""
				release=repodir.replace('/','').lstrip()
				if release.endswith(".gpp"):
					signedby="[Signed-by={}] ".format(release)
				elif release in knowedReleases or release in lastChanceReleases:
					urlRelease=os.path.join(url,release)
					components=self._releaseScrap(session,urlRelease)
					repoUrl.append("deb {3}{0} {1} {2}".format(url.replace('dists/',''),release,' '.join(components),signedby))
				else:
					self._debug("{0} not found in {1}".format(repodir,knowedReleases))
		return(repoUrl)
	#def _scrapDistribution

	def _getSignedBy(self,signedby):
		if "://" in signedby:
			if signedby.lower().startswith("http") and ("gpg" in signedby.lower() or signedby.endswith(".gpg") or signedby.endswith(".asc")):
				scontent=requests.get(signedby)
				if scontent.ok==True:
					fname=os.path.basename(signedby)
					fpath=os.path.join(TRUSTEDDIR,fname)
					if fpath.endswith(".gpg")==False:
						fpath+=".gpg"
					fcontent=scontent.content.decode()
					if os.path.exists(TRUSTEDDIR)==False:
						os.makedirs(TRUSTEDDIR)
					ftemp=tempfile.NamedTemporaryFile()
					with open(ftemp.name,"w") as f:
						f.write(fcontent)
					if os.path.exists(fpath):
						os.unlink(fpath)
					cmd=["gpg","--dearmor","-o",fpath,ftemp.name]
					subprocess.run(cmd)
					ftemp.close()
					signedby=fpath
		elif len(signedby)<110:
			if signedby.startswith("/")==True and os.path.exists(signedby)==True:
				if os.path.exists(TRUSTEDDIR)==False:
					os.makedirs(TRUSTEDDIR)
				fname=os.path.basename(signedby)
				fpath=os.path.join(TRUSTEDDIR,fname)
				if fpath!=signedby:
					shutil.copy2(signedby,fpath)
				signedby=fpath
		return(signedby)

	def addRepo(self,url,name="",desc="",signedby=""):
		error=errorEnum.NO_ERROR
		desc=desc.strip()
		debparms=""
		if url.endswith("/")==False:
			url+="/"
		decompurl=url.split(":/")
		if len(decompurl)<=1:
			error=errorEnum.MALFORMED
		else:
			repodata={}
			data=decompurl[-1].split(" ")
			if len(decompurl[0].split(" "))>1:
				debparms="{} ".format(" ".join(decompurl[0].split(" ")[:-1]))
				deburl="{0}:/{1}".format(decompurl[0].split(" ")[-1],data[0])
			else:
				deburl="{0}:/{1}".format(decompurl[0],data[0])
			if name=="":
				if len(data)>1:
					name="{0}_{1}".format(data[0],data[1]).replace("/","_").replace(":",".")
				else:
					name="{0}".format(data[0]).replace("/","_").replace(":",".")
			if len(data)>2:
				data=" ".join(data[1:])
				fcontent=["deb {0}{1} {2}".format(debparms,deburl,data)]
			else:
				session=self._requestSession()
				if len(data)==2:
					deburl="{}/dists/{}".format(deburl,data[1])
					components=self._releaseScrap(session,deburl)
					fcontent=["deb {0} {1}".format(url.replace('dists',''),' '.join(components))]
				else:
					fcontent,repodata=self._repositoryScrap(session,deburl)
			repo=_repoFile()
			if name=="" or name=="auto":
				altname="{}_{}".format(url.rstrip("/").split("/")[-2],url.rstrip("/").split("/")[-1])
				name=repodata.get("name","")
				if name=="":
					name=altname
			if name.endswith(".sources")==True:
				name=name.replace(".sources","")
			if desc=="" or desc=="auto":
				desc=repodata.get("desc","")
				if desc=="":
					desc=url
			fpath=os.path.join(SOURCESDIR,"{}.sources".format(name))
			repo.setFile(fpath.replace(".sources",".list"))
			repo.raw="\n".join(fcontent)
			fcontent=repo.getRepoDEB822()
			repo.setFile(fpath)
			repo.raw=fcontent
			if url not in fcontent.keys():
				if url.endswith("/")==False:
					url+="/"
			if url not in fcontent.keys():
				error=errorEnum.URL_NOT_FOUND
			else:
				fcontent[url]["format"]="sources"
				fcontent[url]["file"]=fpath
				fcontent[url]["Name"]=name
				fcontent[url]["Description"]=desc
				if signedby!="":
					fcontent[url]["Signed-By"]=self._getSignedBy(signedby)
				error=repo.writeFromData(fcontent[url])
		return(error)
	#def addRepo
