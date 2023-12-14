#/usr/bin/env python3
import os,sys,shutil
import json
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import re


class manager():
	def __init__(self):
		self.dbg=True
		self.sourcesFile="/etc/apt/sources.list"
		self.sourcesDir="/etc/apt/sources.list.d"
		self.managerDir="/usr/share/repoman/sources.d"
	#def __init__
	
	def _debug(self,msg):
		if self.dbg==True:
			print("{}".format(msg))
	#def _debug

	def _formatRepoLine(self,repoline,file=""):
		data={}
		repoType=repoline.split(":/")[0].split(" ")[-1]
		if ":/" not in repoline:
			return(data)
		repoUrl="{}:/{}".format(repoType,repoline.split(":/")[1].split(" ")[0])
		if len(repoUrl)>0:
			repoRelease="{}".format(repoline.split(":/")[1].split(" ")[1])
			if len(repoRelease)>0:
				if repoUrl not in data.keys():
					data[repoUrl]={}
				if repoRelease not in data[repoUrl].keys():
					data[repoUrl][repoRelease]={}
				repoComponents=list(set(repoline.split(":/")[1].split(" ")[2:]))
				if repoComponents.count("")>0:
					repoComponents.remove("")
				data[repoUrl][repoRelease]={"components":repoComponents,"file":file,"raw":repoline,"name":os.path.basename(file),"desc":""}
		return(data)
	#def _formatRepoLine

	def _mergeData(self,dest,source):
		dest["components"]=list(set(dest.get("components",[])+source.get("components",[])))
		raw=dest.get("raw","").split(":/")
		if len(raw)==2:
			rawline="{0}:/{1} {2}".format(raw[0]," ".join(raw[1].split(" ")[:2])," ".join(dest["components"]))
			dest["raw"]=rawline
		return(dest)
	#def _mergeData

	def _getFileContent(self,fname):
		fcontent=""
		if os.path.exists(fname):
			try:
				with open(fname,"r") as f:
					fcontent=f.read()
			except Exception as e:
				print(e)
		return(fcontent)
	#def _getFileContent

	def _jsonFromContents(self,file,contents):
		data={}
		if isinstance(contents,str):
			contents=contents.split("\n")
		for fline in contents:
			fline=fline.replace("\t"," ")
			fline=fline.strip()
			rawLine=fline
			if fline.startswith("deb") and ":/" in fline:
				dataline=self._formatRepoLine(fline,file)
				for url,urldata in dataline.items():
					if url not in data.keys():
						data[url]={}
					for release in urldata.keys():
						if release not in data[url].keys():
							data[url][release]={}
						urldata[release]=self._mergeData(urldata[release],data[url][release])
						data[url][release]=urldata[release]
		return(data)
	#def _jsonFromContents

	def _readSourcesFile(self,sourcesF):
		data={}
		if os.path.exists(sourcesF):
			fcontent=self._getFileContent(sourcesF)
			data=self._jsonFromContents(sourcesF,fcontent)
		return(data)
	#def _readSourcesFile
	
	def _readSourcesDir(self,dirF):
		repos={}
		if os.path.isdir(dirF):
			for f in os.scandir(dirF):
				if f.is_dir():
					self._readSourcesDir(f.path)
				data=self._readSourcesFile(f.path)
				for dataurl,dataitems in data.items():
					if len(repos.get(dataurl,''))==0:
						repos.update({dataurl:dataitems})
		return(repos)
	#def _readSourcesDir

	def _readJsonFile(self,jsonF):
		data={}
		if os.path.exists(jsonF):
			try:
				jcontent=json.loads(self._getFileContent(jsonF))
			except Exception as e:
				print("Err: {}".format(e))
				return(data)
			for reponame,repodata in jcontent.items():
				repolines=repodata.get("repos")
				for fline in repolines:
					dataline=self._formatRepoLine(fline)
					for url,urldata in dataline.items():
						if url not in data.keys():
							data[url]={}
						for release in urldata.keys():
							if release not in data[url].keys():
								data[url][release]={}
							urldata[release]=self._mergeData(urldata[release],data[url][release])
							data[url][release]=urldata[release]
				for url,urldata in data.items():
					for release,releasedata in urldata.items():
						releasedata["name"]=reponame
						releasedata["desc"]=repodata.get("desc","")
						releasedata["file"]=self._getSourcesPathFromJson(jsonF)
		return(data)
	#def _readJsonFile

	def _readManagerDir(self,dirF):
		repos={}
		if os.path.isdir(dirF):
			for f in os.scandir(dirF):
				if os.path.isdir(f.path):
					repos.update(self._readManagerDir(f.path))
				else:
					data=self._readJsonFile(f.path)
					for dataurl,dataitems in data.items():
						if len(repos.get(dataurl,''))==0:
							repos.update({dataurl:dataitems})
		return(repos)
	#def _readManagerDir(self,dirF):

	def _writeJsonFromSources(self,file,content):
		if file.endswith(".list") and (file!=self.sourcesFile):
			jfile=os.path.join(self.managerDir,os.path.basename(file.replace(".list",".json")))
			if os.path.exists(jfile)==False:
				for f in os.scandir(self.managerDir):
					if os.path.basename(f).lower()==os.path.basename(jfile).lower():
						jfile=f.path
						break
		elif file==self.sourcesFile:
			if len(content)>0:
				jfile=self._getDefaultJsonFromDefaultRepo(content[0])
			jfile=os.path.join(self.managerDir,file.replace(".list",".json"))
		self._debug("Json File: {}".format(jfile))
		jcontent={}
		if len(content)>0:
			newcontent=[]
			for line in content:
				newcontent.append(line.replace("// ","/ "))
			content=newcontent
			self._debug(": {}".format(file))
			try:
				jcontent=json.loads(self._getFileContent(jfile))
			except Exception as e:
				self._debug("{} load error".format(jfile))
				self._debug("{}".format(e))
			if len(jcontent)>0:
				for name,namedata in jcontent.items():
					repos=list(set(namedata.get("repos",[])+content))
					namedata["repos"]=repos
			else:
				data=self._formatRepoLine(content[0],file)
				url=list(data.keys())[0]
				release=list(data[url].keys())[0]
				name=data[url][release].get("name",os.path.basename(file)).replace(".json","")
				jcontent[name]={"changed":False,"desc":"","enabled":True,"repos":content}
			with open(jfile,'w') as f:
				json.dump(jcontent,f,indent=4)
	#def _writeJsonFromSources

	def _getDefaultJsonFromDefaultRepo(self,repoline):
		file=""
		if "http://lliurex.net" in repoline:
			for f in os.listdir(os.path.join(self.managerDir,"default")):
				if f.lower().startswith("lliurex_") and "mirror" not in f.lower():
					file="default/{}".format(f)
					break
		elif "http://mirror" in repoline:
			for f in os.listdir(os.path.join(self.managerDir,"default")):
				if f.lower().startswith("lliurex_mirror"):
					file="default/{}".format(f)
					break
		elif "ubuntu" in repoline:
			for f in os.listdir(os.path.join(self.managerDir,"default")):
				if f.lower().startswith("ubuntu"):
					file="default/{}".format(f)
					break
		return(file)
	#def _getDefaultJsonFromDefaultRepo

	def _getSourcesPathFromJson(self,file):
		if os.path.dirname(file)==os.path.join(self.managerDir,"default"):
			file=self.sourcesFile
		else:
			file=os.path.join(self.sourcesDir,os.path.basename(file).replace(".json",".list"))
			if os.path.exists(file)==False:
				for f in os.scandir(self.sourcesDir):
					if os.path.basename(f).lower()==os.path.basename(file).lower():
						file=f.path
						break
		return(file)
	#def _getSourcesPathFromJson

	def sortContents(self,contents):
		sortcontent=[]
		mirrorLines=0
		for line in contents:
			if "lliurex.net" in line:
				idx=mirrorLines
			elif "/mirror/llx" in line:
				idx=0
				mirrorLines+=1
			else:
				idx=len(sortcontent)
			line=line.replace("// ","/ ")
			sortcontent.insert(idx,line)
		return(sortcontent)
	#def _sortContents

	def _writeSourceFile(self,file,content):
		#Sort content
		sortcontent=self.sortContents(content)
		with open(file,"w") as f:
			for line in sortcontent:
				line=line.replace("deb","").strip()
				if len(line.strip())>0:
					if line.startswith("#"):
						line="#deb  {}\n".format(line.replace("#","",1))
					else:
						line="deb  {}\n".format(line)
					line=line.replace("\t"," ")
					formatline=[]
					for l in line.split(" "):
						if len(l)>0:
							if l.endswith("//"):
								l=l[:-1]
							formatline.append(l)
					line=" ".join(formatline)
					f.write(line)
	#def _writeSourceFile

	def _getJsonPathFromSources(self,file,defaultRepoName=""):
		if file==self.sourcesFile:
			file=os.path.join(self.managerDir,"default",os.path.basename(file).replace(".list",".json"))
		else:
			file=os.path.join(self.managerDir,os.path.basename(file).replace(".list",".json"))
			if os.path.exists(file)==False:
				for f in os.scandir(self.managerDir):
					if os.path.basename(f).lower()==os.path.basename(file).lower():
						file=f.path
						break
		return(file)
	#def _getJsonPathFromSources

	def _searchUrlNameDescFromJson(self,url,managerRepos):
		name=url
		desc=""
		for repo in managerRepos.keys():
			if repo==url:
				for release,data in managerRepos[url].items():
					name=data.get("name","")
					if name=="":
						name=data.get("file",url)
					desc=data.get("desc","")
					break
				if name!=url:
					break
		return(name,desc)
	#def _searchUrlName

	def _compareRepos(self,source,compare):
		enabled=True
		if len(source)!=len(compare):
			enabled=False
		elif len(set(set(source)-set(compare)))>0:
			enabled=False
		elif len(set(set(compare)-set(source)))>0:
			enabled=False
		return enabled
	#def _compareRepos

	def _sortRepoJson(self,repos):
		sortrepos=repos
		return(sortrepos)
	#def _sortRepoJson

	def getRepos(self):
		repos={}
		sourcesRepo=self._readSourcesFile(self.sourcesFile)
		extraRepos=sourcesRepo.copy()
		extraRepos=self._readSourcesDir(self.sourcesDir)
		extraRepos.update(sourcesRepo)
		managerRepos=self._readManagerDir(self.managerDir)
		managerUrl=managerRepos.keys()
		extraUrl=set(set(extraRepos.keys()-set(managerUrl)))
		for url in managerUrl:
			(name,desc)=self._searchUrlNameDescFromJson(url,managerRepos)
			enabled=False
			managerReleases=[]
			if len(extraRepos.get(url,''))>0:
				enabled=True
				managerReleases=managerRepos[url].keys()
				extraReleases=extraRepos[url].keys()
				enabled=self._compareRepos(managerReleases,extraReleases)
			for release in managerReleases:
				if enabled==True:
					managerRepos[url][release]["name"]=name
					managerRepos[url][release]["desc"]=desc
					components=list(set(managerRepos[url][release]["components"]))
					extracomps=extraRepos[url].get(release,{}).get("components",[])
					enabled=self._compareRepos(components,extracomps)
				managerRepos[url][release].update({"enabled":enabled})
			repos[url]=managerRepos[url]
		for url in extraUrl:
			for key,data in extraRepos.items():
				newdata=data.copy()
				for datakey,dataitem in data.items():
					newdata[datakey].update({"enabled":True})
				repos.update({key:newdata})
		repos=self._sortRepoJson(repos)
		return(repos)
	#def getRepos

	def _getRepoByName(self,name):
		repos=self.getRepos().copy()
		ret={}
		for repo,repodata in repos.items():
			for release,releasedata in repodata.items():
				if name.replace(" ","").strip().lower()==releasedata.get("name","").replace(" ","").strip().lower():
					ret={repo:repos[repo]}
					break
			if len(ret)>0:
				break
		return(ret)
	#def _getRepoByName

	def disableRepoByName(self,name):
		repo=self._getRepoByName(name)
		repos=[]
		file=""
		url=""
		for repourl,repourldata in repo.items():
			for release,releasedata in repourldata.items():
				if os.path.exists(releasedata.get("file","")):
					file=releasedata.get("file","")
					url=repourl
					break
		if file.endswith(".json"):
			file=self._getSourcesPathFromJson(file)
		if len(file)>0:
			fcontent=self._getFileContent(file)
			newcontent=[]
			delcontent=[]
			for line in fcontent.split("\n"):
				if url.replace(" ","").strip() not in line.replace(" ","").strip() and len(line.strip())>0:
					if line.startswith("deb")==False:
						line="deb {}".format(line)
					newcontent.append(line.replace("// ","/ "))
				elif len(line.strip())>0:
					if line.startswith("deb")==False:
						line="deb {}".format(line)
					delcontent.append(line)
			if len(delcontent)>0:
				self._writeJsonFromSources(file,delcontent)
			self._writeSourceFile(file,newcontent)
	#def disableRepoByName(self,name):

	def enableRepoByName(self,name):
		repo=self._getRepoByName(name)
		repos=[]
		file=""
		for url,urldata in repo.items():
			for release,releasedata in urldata.items():
				if os.path.exists(releasedata.get("file","")):
					if file=="":
						file=releasedata.get("file","")
					raw=releasedata.get("raw","") 
					if len(raw.strip())>0:
						if raw.startswith("deb")==False:
							raw="deb {}".format(raw)
						repos.append("{}".format(raw))
		if file.endswith(".json"):
			file=self._getSourcesPathFromJson(file)
		if len(file)>0:
			newcontent=[]
			fcontent=self._getFileContent(file)
			for line in fcontent.split("\n"):
				if url.replace(" ","").strip() not in line.replace(" ","").strip() and len(line.strip())>0:
					newcontent.append(line)
			newcontent.extend(repos)
			self._writeSourceFile(file,newcontent)
	#def enableRepoByName(self,name):

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
		self._debug("Reading {}".format(url))
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
		knowedReleases=["jammy","jammy-updates","jammy-security","stable","unstable"]
		self._debug("Reading {}".format(url))
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
				if release in knowedReleases:
					urlRelease=os.path.join(url,release)
					components=self._releaseScrap(session,urlRelease)
					repoUrl.append("deb {0} {1} {2}".format(url.replace('dists',''),release,' '.join(components)))
				else:
					self._debug("{0} not found in {1}".format(repodir,knowedReleases))
		return repoUrl
	#def _repositoryScrap

	def _requestSession(self):
		session=requests.Session()
		retry=Retry(connect=3, backoff_factor=0.5)
		adapter=HTTPAdapter(max_retries=retry,pool_block=True)
		session.mount('http://',adapter)
		session.mount('https:',adapter)
		return session
	#def _requestSession

	def addRepo(self,url,name="",desc=""):
		url=url.replace("deb ","")
		debparms=""
		decompurl=url.split(":/")
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
			sourceF=os.path.join(self.sourcesDir,"{}.list".format(name))
			jsonF=os.path.join(self.managerDir,"{}.json".format(name))
			if len(fcontent)>0:
				self._writeSourceFile(sourceF,fcontent)
				self._writeJsonFromSources(sourceF,fcontent)
	#def addRepo
#def class manager

class RepoManager():
	def __init__():
		return(manager)
