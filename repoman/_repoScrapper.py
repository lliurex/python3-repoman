#/usr/bin/env python3
import os
from . import _repoFile 
from . import _configManager
import requests
import subprocess
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from bs4 import BeautifulSoup

BASEDIR="/etc/apt"
SOURCESDIR=os.path.join(BASEDIR,"sources.list.d")

class _repoScrapper():
	def __init__(self):
		self.dbg=True
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
			self._debug("Error conneting to  {}: {}".format(url,e))
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
		for component in releaseDirs:
			component=component.replace('/','').lstrip()
			self._debug("Inspect releasedir {}".format(component))
			if component in knowedComponents:
				components.append(component)
		return(components)
	#def _releaseScrap

	def _repositoryScrap(self,session,url):
		repoUrl=[]
		cmd=["lsb_release","-c"]
		output=subprocess.check_output(cmd,encoding="utf8").strip().replace("\t"," ")
		codename=output.split(" ")[-1]
		knowedReleases=[codename,"{0}-updates".format(codename),"{0}-security".format(codename),"stable","unstable"]
		lastChance=url.rstrip("/").split("/")[-1]
		lastChanceReleases=[lastChance,"{0}-updates".format(lastChance),"{0}-security".format(lastChance)]
		self._debug("Repo Reading {}".format(url))
		dirlist=self._readServerDir(session,url)
		if "dists/" in dirlist:
			url=os.path.join(url,"dists/")
		elif "/dists" not in url:
			self._debug("dists not found")
			return(repoUrl)
		dirlist=self._readServerDir(session,url)
		if url.endswith('/dists/'):
			for repodir in dirlist:
				release=repodir.replace('/','').lstrip()
				if release in knowedReleases or release in lastChanceReleases:
					urlRelease=os.path.join(url,release)
					components=self._releaseScrap(session,urlRelease)
					repoUrl.append("deb {0} {1} {2}".format(url.replace('dists/',''),release,' '.join(components)))
				else:
					self._debug("{0} not found in {1}".format(repodir,knowedReleases))
		return repoUrl
	#def _repositoryScrap

	def addRepo(self,url,name="",desc=""):
		ret=1
		debparms=""
		if url.endswith("/")==False:
			url+="/"
		decompurl=url.split(":/")
		jfile=""
		if len(decompurl)>1:
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
					fcontent=self._repositoryScrap(session,deburl)
			#REM
			#FILENAME NOT ASSOC WITH NEW SOurCES FILE
			repo=_repoFile()
			name="{}_{}.list".format(url.rstrip("/").split("/")[-2],url.rstrip("/").split("/")[-1])
			fpath=os.path.join(SOURCESDIR,name)
			repo.setFile(fpath)
			repo.raw="\n".join(fcontent)
			fcontent=repo.getRepoDEB822()
			print(fcontent[url])
			repo.writeFromData(fcontent[url])

	#		sourceF=os.path.join(self.sourcesDir,"{}.list".format(name.replace(" ","_")))
	#		jsonF=os.path.join(self.managerDir,"{}.json".format(name.replace(" ","_")))
	#		if len(fcontent)>0:
	#			self._writeSourceFile(sourceF,fcontent)
	#			jfile=self._writeJsonFromSources(sourceF,fcontent,name=name,desc=desc)
	#			ret=0
	#		afterAdd=self.getRepos()
	#		if len(beforAdd)==len(afterAdd):
	#			if os.path.isfile(sourceF):
	#				self._debug("Deleting {} (duplicated)".format(sourceF))
	#				os.unlink(sourceF)
	#			if os.path.isfile(jfile):
	#				self._debug("Deleting {} (duplicated)".format(jfile))
	#				os.unlink(jfile)
	#def addRepo
