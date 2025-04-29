#/usr/bin/env python3
import os,sys,shutil
import json
import subprocess
try:
	from appconfig import appConfigN4d
except:
	appConfigN4d=None
import requests
import subprocess
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from bs4 import BeautifulSoup


class manager():
	def __init__(self):
		self.sourcesFile="/etc/apt/sources.list"
		self.sourcesDir="/etc/apt/sources.list.d"
		self.managerDir="/usr/share/repoman/sources.d"
		self.dbg=False
	#def __init__
	
	def _debug(self,msg):
		if self.dbg==True:
			print("{}".format(msg))
	#def _debug

	def _sanitizeString(self,line):
		line=line.replace("/t"," ")
		line=line.strip()
		sline=""
		for item in line.split(" "):
			if len(item)>0:
				if item.endswith("//"):
					item=item[:-1]
				sline+="{} ".format(item)
		sline=sline.strip()
		return(sline)
	#def _sanitizeString

	def _formatRepoLine(self,repoline,file=""):
		data={}
		repoline=self._sanitizeString(repoline)
		urlType=repoline.split(":/",1)[0].split(" ")[-1]
		repoType=repoline.split(":/",1)[0].split(" ")[0]
		if ":/" not in repoline:
			return(data)
		repoUrl="{}:/{}".format(urlType,repoline.split(":/",1)[1].split(" ")[0])
		if len(repoUrl)>0 and repoline.split(":/",1)[1].strip().count(" ") > 0:
			repoRelease="{}".format(repoline.split(":/",1)[1].split(" ")[1])
			if len(repoRelease)>0:
				if repoUrl[-1]!="/":
					repoUrl+="/"
				if repoUrl not in data.keys():
					data[repoUrl]={}
				if repoRelease not in data[repoUrl].keys():
					data[repoUrl][repoRelease]={}
				repoComponents=list(set(repoline.split(":/",1)[1].split(" ")[2:]))
				if repoComponents.count("")>0:
					repoComponents.remove("")
				repoComponents.sort()
				url=repoUrl.strip("/").split("/")
				if len(url)>2:
					name="{0}.{1}".format(url[2],url[-1])
				else:
					name="{0}_{1}".format(os.path.basename(file),url[-1])
				if "deb-src" in repoType:
					repoRelease+="-src"
				data[repoUrl][repoRelease]={"components":repoComponents,"file":file,"raw":repoline,"name":name,"desc":""}
		return(data)
	#def _formatRepoLine

	def _mergeData(self,dest,source):
		destComponents=dest.get("components",[])
		destComponents.sort()
		sourceComponents=source.get("components",[])
		sourceComponents.sort()
		dest["components"]=list(set(destComponents+sourceComponents))
		dest["components"].sort()
		raw=dest.get("raw","").split(":/",1)
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

	def _isFormatSources(self,contents):
		sources=True
		if len(contents)>0:
			strcontents="\n".join(contents)
			if "Types" in strcontents.split(":"):
				sources=False
		return(sources)
	#def _isFormatSources

	def _getRepoContents(self,file,contents):
		data={}
		for fline in contents:
			fline=self._sanitizeString(fline)
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
					data[url]=self._sortRepoComponents(data[url])
		return(data)
	#def _getRepoContents

	def _getSourcesFileContents(self,file,contents):
		repolines=[]
		cont=0
		for fline in contents:
			fline=self._sanitizeString(fline)
			(key,data)=fline.split(":")[0],":".join(fline.split(":")[1:])
			if key.lower()=="types":
				cont+=1
				types=data
			if key.lower()=="uris":
				cont+=1
				url=data
				if url[-1]!="/":
					url+="/"
			if key.lower()=="suites":
				cont+=1
				releases=data
			if key.lower()=="components":
				cont+=1
				components=data
			if key.lower()=="architectures":
				architectures=data
			if key.lower()=="signed-by":
				signed=" [signed-by={}] ".format(self._sanitizeString(data))
		if cont==4:
			for release in releases.split():
				repolines.append("{0}{1}{2} {3} {4}".format(types,signed,url,release,components))
		return(self._getRepoContents(file,repolines))
	#def _getRepoContents

	def _translateListToSourceS(self,content):

	def _jsonFromContents(self,file,contents):
		data={}
		if isinstance(contents,str):
			contents=contents.split("\n")
		if self._isFormatSources(contents)==True
			data=self._getSourcesFileContents(file,contents)
		else:
			data=self._getRepoContents(file,contents)
		return(data)
	#def _jsonFromContents

	def readSourcesFile(self,sourcesF):
		data={}
		self._debug("Read Sources {}".format(sourcesF))
		if os.path.exists(sourcesF):
			fcontent=self._getFileContent(sourcesF)
			data=self._jsonFromContents(sourcesF,fcontent)
		return(data)
	#def readSourcesFile
	
	def _readSourcesDir(self,dirF):
		repos={}
		if os.path.isdir(dirF):
			for f in os.scandir(dirF):
				if f.is_dir():
					self._readSourcesDir(f.path)
				if f.path.endswith(".list") or f.path.endswith(".sources"):
					data=self.readSourcesFile(f.path)
					for dataurl,dataitems in data.items():
						if not dataurl in repos.keys():
							repos.update({dataurl:dataitems})
		return(repos)
	#def _readSourcesDir

	def _readJsonFile(self,jsonF):
		data={}
		if os.path.exists(jsonF)==False:
			self._debug("{} not found!!!".format(jsonF))
			return(data)
		try:
			jcontent=json.loads(self._getFileContent(jsonF))
		except Exception as e:
			self._debug("Err: {}".format(e))
			return(data)
		for reponame,repodata in jcontent.items():
			repolines=repodata.get("repos",[])
			for fline in repolines:
				dataline=self._formatRepoLine(fline)
				for url,urldata in dataline.items():
					if url.endswith("/")==False:
						url+="/"
					if url not in data.keys():
						data[url]={}
					for release in urldata.keys():
						if release not in data[url].keys():
							data[url][release]={}
						urldata[release]=self._mergeData(urldata[release],data[url][release])
						data[url][release]=urldata[release]
			for url,urldata in data.items():
				for release,releasedata in urldata.items():
					releasedata["desc"]=repodata.get("desc","")
					releasedata["file"]=repodata.get("file","")
					if releasedata.get("file","")=="":
						releasedata["file"]=self._getSourcesPathFromJson(jsonF)
					name=reponame
					if reponame.split("_")[0]==os.path.basename(releasedata["file"]):
						if len(reponame.split("_"))>1:
							name="{0}_{1}".format(reponame.split("_")[0],os.path.basename(url.strip("/").split("/")[-1]))
					releasedata["name"]=name
					releasedata["available"]=True
					if url.startswith("http://mirror/"):
						releasedata["available"]=self.isMirrorEnabled()
		return(data)
	#def _readJsonFile

	def writeJsonFile(self,jfile,content):
		sw=False
		if os.path.isdir(os.path.dirname(jfile))==True:
			try:
				with open(jfile,'w') as f:
					json.dump(content,f,indent=4)
				sw=True
			except:
				print("BIG FAIL: {} isn't a regular file".format(jfile))
		return(sw)
	#def writeJsonFile

	def _writeJsonFromSources(self,file,content,**kwargs):
		if self._isFormatSources(content)==True:
			content=self._getSourcesFileContents(file,content)
		if len(content)<=0:
			return
		jfile=self.getJsonPathFromSources(file,content)
		self._debug("Json File: {}".format(jfile))
		jcontent={}
		newcontent=[]
		for line in content:
			newcontent.append(self._sanitizeString(line).replace("#",""))
		content=newcontent
		self._debug(": {}".format(file))
		try:
			jcontent=json.loads(self._getFileContent(jfile))
		except Exception as e:
			self._debug("{} load error".format(jfile))
			self._debug("{}".format(e))
		if len(jcontent)>0:
			for name,namedata in jcontent.items():
				repos=list(set(self._formatReposForJson(namedata.get("repos"))+content))
				namedata["repos"]=repos
		else:
			data=self._formatRepoLine(content[0],file)
			url=list(data.keys())[0]
			release=list(data[url].keys())[0]
			name=data[url][release].get("name",os.path.basename(file)).replace(".json","")
			name=kwargs.get("name",name)
			desc=kwargs.get("desc","")
			jcontent[name]={"changed":False,"desc":desc,"enabled":True,"repos":content}
		if name in jcontent.keys():
			jcontent[name].update({"file":file})
		self._debug("Attempting to write {}".format(jfile))
		self._debug(jcontent)
		self._debug("< EOF")
		self.writeJsonFile(jfile,jcontent)
		return(jfile)
	#def _writeJsonFromSources

	def _writeSourceFile(self,file,content):
		#Sort content
		#Get format for content. If it's old format (aka .list) and file not exists
		#or in the case that the file exists and it's a sources one then write new format
		#REM TODO
		old=True
		if is.path.exists(file):
			oldContent=self._getreadSourcesFile(file)
			old=self._isFormatSources(oldContent)
		sortContent=self.sortContents(content)
		if old==True:
			sortContent=self._translateListToSources(sortContent)
		with open(file,"w") as f:
			for line in sortContent:
				line=self._sanitizeString(line)
				if len(line)>0:
				#	if not line.startswith("deb") and line[0]!="#":
				#		line="deb {}".format(line)
					if line.endswith("\n")==False:
						line+="\n"
					f.write(line)
	#def _writeSourceFile

	def _readManagerDir(self,dirF):
		repos={}
		if os.path.isdir(dirF):
			for f in os.scandir(dirF):
				if os.path.isdir(f.path):
					repos.update(self._readManagerDir(f.path))
				else:
					data=self._readJsonFile(f.path)
					for repoUrl,repoItems in data.items():
						if len(repos.get(repoUrl,''))==0:
							if repoUrl[-1]!="/":
								repoUrl+="/"
							repos.update({repoUrl:repoItems})
		return(repos)
	#def _readManagerDir(self,dirF):

	def _formatReposForJson(self,repos):
		sortrepos=[]
		for repo in repos:
			raw=self._formatRepoLine(repo).get("raw","")
			if len(raw)>0:
				sortrepos.append(raw.replace("#",""))
		return(sortrepos)
	#def _formatReposForJson

	def _getDefaultJsonFromDefaultRepo(self,repoline):
		file=""
		self._debug("Get {} for searching".format(repoline))
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
			files=[os.path.join(self.sourcesDir,os.path.basename(file).replace(".json",".list")),os.path.join(self.sourcesDir,os.path.basename(file).replace(".json",".sources"))]
			for file in files:
				if os.path.exists(file):
					 break
			if os.path.exists(file)==False:
				file=os.path.join(self.sourcesDir,os.path.basename(file).replace(".list",".sources"))
				if os.path.exists(file)==False:
					for f in os.scandir(self.sourcesDir):
						if f.name.lower()==os.path.basename(file).lower():
							file=f.path
							break
		return(file)
	#def _getSourcesPathFromJson

	def getSourcesPathFromPpa(self,ppa):
		sppa="".join(ppa.split(":")[1:]).split("/")
		for f in os.scandir(self.sourcesDir):
			if sppa[0] in f.name and sppa[1] in f.name and f.name.count("-")>=3:
				file=f.path
		return(file)
	#def getSourcesPathFromPpa

	def sortContents(self,contents):
		sortcontent=[]
		mirrorLines=0
		llxLines=0
		contents.sort()
		for line in contents:
			line=self._sanitizeString(line)
			if "lliurex.net" in line:
				idx=mirrorLines
				llxLines+1
			elif "/mirror/llx" in line:
				idx=0
				mirrorLines+=1
			elif "http://archive.ubuntu.com/ubuntu/" in line:
				idx=mirrorLines+llxLines
			else:
				idx=len(sortcontent)
			sortcontent.insert(idx,line)
		return(sortcontent)
	#def _sortContents

	def _sortRepoComponents(self,repo):
		for release,releasedata in repo.items():
			releasedata["components"].sort()
		return(repo)
	#def _sortRepoComponents

	def _sortRepoJson(self,repos):
		sortrepos=repos[1]
		key=list(sortrepos.keys())[0]
		file=sortrepos[key]["file"]
		name=sortrepos[key]["name"]
		val=ord(name[0].lower())
		if file==self.sourcesFile:
			if "mirror" in name.lower():
				val=0
			elif "lliurex" in name.lower():
				val=1
			elif "ubuntu" in name.lower():
				val=2
		return(val)
	#def _sortRepoJson

	def _sortRepos(self,repos):
		sortrepos={}
		for repo in sorted(repos.items(),key=self._sortRepoJson):
			(key,data)=repo
			data=self._sortRepoComponents(data)
			sortrepos[key]=data
		return(sortrepos)
	#def _sortRepos
	
	def _sortRepoByName(self,repos):
		sortrepos=repos[1]
		key=repos[0]
		file=sortrepos["file"]
		val=ord(key[0].lower())
		if file==self.sourcesFile:
			if "mirror" in key.lower():
				val=0
			elif "lliurex" in key.lower():
				val=1
			elif "ubuntu" in key.lower():
				val=2
		return(val)
	#def _sortRepoByName

	def _sortReposByName(self,repos):
		sortrepos={}
		for repo in sorted(repos.items(),key=self._sortRepoByName):
			(name,data)=repo
			sortrepos[name]=data
		return(sortrepos)
	#def _sortReposByName

	def sortJsonRepos(self,repos):
		jsonrepos={}
		sortrepos={}
		for url in self.sortContents(list(repos.keys())):
			for release,releasedata in repos[url].items():
				name=releasedata.get("name","")
				desc=releasedata.get("desc","")
				file=releasedata.get("file","")
				available=releasedata.get("available",False)
				if name not in jsonrepos.keys() and len(name)>0:
					jsonrepos[name]={"desc":desc,"enabled":releasedata.get("enabled",False),"file":file,"available":available}
		return(self._sortReposByName(jsonrepos))
	#def _sortJsonRepos

	def getJsonPathFromSources(self,file,content,defaultRepoName=""):
		jfile=""
		self._debug("Searching for {}".format(file))
		if (file.endswith(".list") or file.endswith(".sources")) and (file!=self.sourcesFile):
			jfile=os.path.join(self.managerDir,os.path.basename(file.replace(".list",".json").replace(".sources",".json")))
			if os.path.exists(jfile)==False:
				for f in os.scandir(self.managerDir):
					if os.path.basename(f).lower()==os.path.basename(jfile).lower():
						jfile=f.path
						break
		elif file==self.sourcesFile:
			jfile=self._getDefaultJsonFromDefaultRepo(content[0])
			jfile=os.path.join(self.managerDir,jfile)
		if jfile=="" or os.path.isdir(jfile)==True:
			#Assign new file
			fname="{}.json".format(content[0].split(":/")[-1].split(" ")[0].replace("/","_"))
			jfile=os.path.join(self.managerDir,fname)
		return(jfile)
	#def getJsonPathFromSources

	def _searchUrlNameDescFromJson(self,url,managerRepos):
		name=url
		desc=""
		for repo in managerRepos.keys():
			if repo==url:
				for release,data in managerRepos[url].items():
					name=data.get("name","")
					if len(name)<=0:
						name="{0}_{1}".format(data.get("file",""),url.strip("/").split("/")[-1])
					desc=data.get("desc","")
					break
				if name!=url:
					break
		return(name,desc)
	#def _searchUrlNameDescFromJson

	def _compareRepos(self,source,compare):
		enabled=True
		source.sort()
		compare.sort()
		if len(source)!=len(compare):
			enabled=False
		elif len(set(set(source)-set(compare)))>0:
			enabled=False
		elif len(set(set(compare)-set(source)))>0:
			enabled=False
		elif len(compare)==0 and len(source)==0:
			enabled=False
		return enabled
	#def _compareRepos

	def getRepos(self):
		repos={}
		sourcesRepo=self.readSourcesFile(self.sourcesFile)
		extraRepos=self._readSourcesDir(self.sourcesDir)
		extraRepos.update(sourcesRepo)
		managerRepos=self._readManagerDir(self.managerDir)
		managerUrl=managerRepos.keys()
		extraUrl=set(set(extraRepos.keys()-set(managerUrl)))
		for url in extraUrl:
			for key,data in extraRepos.items():
				newdata=data.copy()
				for datakey,dataitem in data.items():
					newdata[datakey].update({"enabled":True,"available":True})
					newdata[datakey]["components"].sort()
				repos.update({key:newdata})
		for url in managerUrl:
			(name,desc)=self._searchUrlNameDescFromJson(url,managerRepos)
			enabled=True
			if len(extraRepos.get(url,''))>0:
				enabled=self._compareRepos(list(managerRepos[url].keys()),list(extraRepos[url].keys()))
			available=True
			if url.startswith("http://mirror/"):
				available=self.isMirrorEnabled()
			for release in managerRepos[url].keys():
				managerRepos[url][release].update({"name":name,"desc":desc,"available":available})
				#if enabled==True:
				components=list(set(managerRepos[url][release]["components"]))
				extracomps=extraRepos.get(url,{}).get(release,{}).get("components",[])
				enabled=self._compareRepos(components,extracomps)
				managerRepos[url][release].update({"enabled":enabled})
			repos[url]=managerRepos[url]
		sortrepos=self._sortRepos(repos)
		return(sortrepos)
	#def getRepos

	def _generateDefaultRepos(self,lliurex=True):
		cmd=["lsb_release","-c"]
		output=subprocess.check_output(cmd,encoding="utf8").strip().replace("\t"," ")
		codename=output.split(" ")[-1]
		if lliurex==True:
			url="http://lliurex.net/{}/".format(codename)
		else:
			url="http://es.archive.ubuntu.com/ubuntu/"
		lines=[]
		components="main restricted universe multiverse"
		for release in [codename,"{}-security".format(codename),"{}-updates".format(codename)]:
			preschool=""
			if "-" not in release and lliurex==True:
				preschool=" preschool"
			lines.append("deb {} {} {}{}".format(url,release,components,preschool))
		return(lines)
	#def _generateDefaultRepos

	def getLliurexRepos(self):
		return(self._generateDefaultRepos(lliurex=True))
	#def getLliurexRepos

	def getUbuntuRepos(self):
		return(self._generateDefaultRepos(lliurex=False))
	#def getUbuntuRepos

	def _getRepoByName(self,name):
		repos=self.getRepos().copy()
		ret={}
		for repo,repodata in repos.items():
			for release,releasedata in repodata.items():
				if name.replace(" ","").strip().lower()==releasedata.get("name","").replace(" ","").strip().lower():
					ret={repo:repos[repo]}
					break
				elif name.replace(" ","").strip().lower() == releasedata.get("name","").replace(" ","").strip().lower().split(".list")[0].split(".sources")[0]:
					ret={repo:repos[repo]}
					break
			if len(ret)>0:
				break
		return(ret)
	#def _getRepoByName

	def disableRepoByName(self,name):
		repo=self._getRepoByName(name)
		self._debug("Disabling repo {}".format(repo.keys()))
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
			if self._isFormatSources(fcontent.split("\n"))==True:
				tmpcontent=self._getSourcesFileContents(file,fcontent.split("\n"))
				tmprepos=[]
				for release in (tmpcontent[url].keys()):
					raw=tmpcontent[url][release].get("raw","")
					if len(raw)>0:
						tmprepos.append(raw)
				fcontent="\n".join(tmprepos)
			newcontent=[]
			delcontent=[]
			for line in fcontent.split("\n"):
				line=self._sanitizeString(line)
				url=url.rstrip("/")
				if (url.replace(" ","") not in line.replace(" ","")) and len(line)>0:
					if line.startswith("deb")==False and line.startswith("#")==False:
						line="deb {}".format(line)
					newcontent.append(line.replace("// ","/ "))
				elif len(line)>0:
					prefix="#"
					line=line.replace("#","",1)
					if line.startswith("deb")==False:
						prefix+="deb"
					if len(prefix)>1:
						prefix+=" "
					newcontent.append("{0}{1}\n".format(prefix,line.replace("// ","/ ")))
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
					raw=self._sanitizeString(raw)
					if len(raw)>0:
						if raw.startswith("deb")==False and raw.startswith("#")==False:
							raw="deb {}".format(raw)
						repos.append("{}".format(raw))
		if file.endswith(".json"):
			file=self._getSourcesPathFromJson(file)
		if len(file)>0:
			newcontent=[]
			matchUrl=url.replace(" ","").strip()
			fcontent=self._getFileContent(file)
			for line in fcontent.split("\n"):
				fLine=self._formatRepoLine(line)
				lineMatch=list(fLine.keys())
				if len(lineMatch)>0:
					if not (matchUrl in  lineMatch[0]) and (len(lineMatch[0])>0):
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

	def _requestSession(self):
		session=requests.Session()
		retry=Retry(connect=3, backoff_factor=0.5)
		adapter=HTTPAdapter(max_retries=retry,pool_block=True)
		session.mount('http://',adapter)
		session.mount('https:',adapter)
		return session
	#def _requestSession

	def addRepo(self,url,name="",desc=""):
		ret=1
		url=url.replace("deb ","")
		debparms=""
		decompurl=url.split(":/")
		jfile=""
		if len(decompurl)>1:
			beforAdd=self.getRepos()
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
			sourceF=os.path.join(self.sourcesDir,"{}.list".format(name.replace(" ","_")))
			jsonF=os.path.join(self.managerDir,"{}.json".format(name.replace(" ","_")))
			if len(fcontent)>0:
				self._writeSourceFile(sourceF,fcontent)
				jfile=self._writeJsonFromSources(sourceF,fcontent,name=name,desc=desc)
				ret=0
			afterAdd=self.getRepos()
			if len(beforAdd)==len(afterAdd):
				if os.path.isfile(sourceF):
					self._debug("Deleting {} (duplicated)".format(sourceF))
					os.unlink(sourceF)
				if os.path.isfile(jfile):
					self._debug("Deleting {} (duplicated)".format(jfile))
					os.unlink(jfile)
		return(ret)
	#def addRepo

	def chkPinning(self,file=""):
		pin=False
		if len(file)<=0:
			file="/etc/apt/preferences.d/lliurex-pinning"
		fcontent=self._getFileContent(file)
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

	def reversePinning(self,file=""):
		keys=["Package","Pin","Pin-Priority"]
		if len(file)<=0:
			file="/etc/apt/preferences.d/lliurex-pinning"
		sfile=file
		if os.path.exists(file)==False:
			sfile="/usr/share/first-aid-kit/rsrc/lliurex-pinning"
			keys=[]
		fcontent=self._getFileContent(sfile)
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
			with open(file,"w") as f:
				f.writelines(content)
	#def reversePinning

	def isMirrorEnabled(self):
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
	#def isMirrorEnabled
	
	def updateRepos(self):
		cmd=["apt","update"]
		try:
			subprocess.run(cmd)
		except Exception as e:
			print("ERROR: {}".format(e))
	#def updateRepos

	def disableAll(self):
		repos=[]
		for repo,data in self.getRepos().items():
			for reponame,repodata in data.items():
				if reponame not in repos:
					repos.append(repodata.get("name"))
		for repo in repos:
			if len(repo)>0:
				self.disableRepoByName(repo)
	#def disableAll

	def enableDefault(self):
		for f in os.scandir(os.path.join(self.managerDir,"default")):
			if f.name.lower().startswith("lliurex") and "mirror" not in f.name.lower():
				data=self._readJsonFile(f.path).popitem()[1].popitem()[1]
				self._debug("Default: {}".format(data["name"]))
				self.enableRepoByName(data["name"])
				break
	#def enableDefault
		
#def class manager

class RepoManager():
	def __init__():
		return(manager)
