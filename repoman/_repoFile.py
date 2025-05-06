#/usr/bin/env python3
import os,sys,shutil
import yaml

class _jRepo():
	def __init__(self):
		self.type=""
		self.name=""
		self.enabled=False
		self.desc=""
		self.uri=""
		self.suites=[]
		self.components=[]
		self.info=[]
		self.signed=""
		self.file=""
		self.format=""
	#def __init__

	def serialize(self):
		self.suites.sort()
		self.components.sort()
		repo={"Types":self.type,
			"Name":self.name,
			"Enabled":self.enabled,
			"Description":self.desc,
			"URIs":self.uri,
			"Suites": self.suites,
			"Components": self.components,
			"Signed-By": self.signed,
			"info":self.info,
			"format":self.format,
			"file":self.file
			}
		return(repo)
	#def _serialize

	def _generateLinesFromSerial(self,serial):
			dictlines={}
			lines=""
			rawLines={}
			frepo=serial.get("file")
			serial.pop("info")
			serial["Suites"]=" ".join(serial["Suites"])
			lines=yaml.dump(serial)
			for suite in serial["Suites"]:
				line=serial["Types"]
				if serial.get("Enabled",True)==False:
					line="#{}".format(line)
				else:
					line=line.replace("#","")
				if serial.get("Signed-By","")!="":
					line+=" [Signed-By={}]".format(serial["Signed-By"].replace("\"","").replace("\'",""))
				line+=" {}".format(serial["URIs"])
				line+=" {}".format(suite)
				line+=" {}".format(serial["Components"])
				rawLine=list(filter(None,line.strip().replace("#","").split(" ")))
				rawLine.sort()
				rawLines["".join(rawLine)]=line
			if os.path.exists(frepo):
				fcontent=""
				with open(frepo,"r") as f:
					fcontent=f.read()
				dictlines={}
				for l in fcontent.split("\n"):
					line=list(filter(None,l.strip().replace("#","").replace("\"","").replace("\'","").split(" ")))
					line.sort()
					line="".join(line)
					dictlines[line]=l
				dictlines.update(rawLines)
			else:
				dictlines=rawLines.copy()
			for key,line in dictlines.items():
				if len(line)==0:
					continue
				lines+="{}\n".format(line)
			lines.rstrip()
			return(lines)
	#def _generateLinesFromSerial

	def writeToFile(self):
		serial=self.serialize()
		frepo=serial.get("file")
		if serial["Signed-By"]=="":
			serial.pop("Signed-By")
		serial["Components"]=" ".join(serial["Components"])
		if serial["format"]=="sources":
			format=serial.pop("format")
			serial["Suites"]=" ".join(serial["Suites"])
			serial.pop("file")
			serial.pop("info")
			lines=yaml.dump(serial)
		else:
			lines=self._generateLinesFromSerial(serial)
		with open(frepo,"w") as f:
			f.write(lines)
	#def writeToFile(self):
#class _jRepo

class _repoFile():
	def __init__(self):
		self.dbg=True
		self.repos={}
		self.file=""
		self.raw=""
	#def __init__

	def setFile(self,fName):
		self.file=fName
		if os.path.exists(fName):
			try:
				with open(fName,"r") as f:
					fcontent=f.read()
			except Exception as e:
				print("Err reading {}: {}".format(fName,e))
			finally:
				self.raw=fcontent
	#def setFile

	def getRepoDEB822(self):
		repos=[]
		if self.file.endswith(".list"):
			repos=self._loadFromList()
		elif self.file.endswith(".sources"):
			repos=self._loadFromSources()
		return(repos)
	#def getRepoDEB822

	def _loadFromList(self):
		repos={}
		for fline in self.raw.split("\n"):
			data=""
			fline=fline.strip()
			#Check for "[" fields
			if "[" in fline:
				data=fline[fline.index("[")+1:fline.index("]")]
				fline=fline[0:fline.index("[")]+fline[fline.index("]")+2:]
			line=list(filter(None,fline.strip().split(" ")))
			if len(line)<2:
				continue
			repo=_jRepo()
			repo.file=self.file
			repo.type=line[0].replace("#","")
			if line[0].startswith("#")==False:
				repo.enabled=True
			if repo.uri=="":
				repo.uri=line[1]
			#elif repo.uri!=line[1]:
			#	continue
			repo.suites.append(line[2].strip())
			components=line[3:]
			repo.components.extend(components)
			repo.components=list(set(repo.components))
			#Process extradata
			if len(data)>0:
				dataF=data.replace("[","").replace("]","").split(",")
				for field in dataF:
					key,value=field.split("=")
					key=key.lower().split("-")[0].lower()
					if key=="signed":
						repo.signed=value.replace("\"","").replace("\'","")
			repo.name="{}_{}".format(repo.uri.rstrip("/").split("/")[-2],repo.uri.rstrip("/").split("/")[-1])
			repo.format="list"
			if repo.uri in repos:
				repos[repo.uri]["Components"].extend(repo.components)
				repos[repo.uri]["Components"]=list(set(repos[repo.uri]["Components"]))
				repos[repo.uri]["Suites"].extend(repo.suites)
				repos[repo.uri]["Suites"]=list(set(repos[repo.uri]["Suites"]))
				if len(repo.signed)>0:
					repos[repo.uri]["Signed-By"]=repo.signed
				if repo.enabled==True:
					repos[repo.uri]["Enabled"]=True
			else:
				repos[repo.uri]=repo.serialize()
		return(repos)
	#def _loadFromList

	def _loadFromSources(self):
		repo={}
		try:
			yFile=yaml.safe_load(self.raw)
		except Exception as e:
			print("Not a valid file: {} -> {}".format(self.file,e))
		finally:
			if "Enabled" not in yFile.keys():
				yFile["Enabled"]=True
			yFile["file"]=self.file
			if yFile.get("Name","")=="":
				yFile["Name"]="{}_{}".format(yFile["URIs"].rstrip("/").split("/")[-2],yFile["URIs"].rstrip("/").split("/")[-1])
			yFile["format"]="sources"
			fields=["Components","Suites"]
			for f in fields:
				yFile[f]=yFile[f].split()
				yFile[f].sort()
			repo={yFile["URIs"]:yFile.copy()}
		return(repo)
	#def _loadFromSources

	def writeFromData(self,data):
		repo=_jRepo()
		repo.file=data.get("file",self.file)
		repo.type=data["Types"]
		repo.name=data["Name"]
		repo.components=data["Components"]
		repo.suites=data["Suites"]
		repo.signed=data.get("Signed-By","")
		repo.uri=data["URIs"]
		repo.format=data["format"]
		repo.enabled=data["Enabled"]
		repo.writeToFile()
		return(repo)
	#def _loadFromData

	def _writeRepoSources(self):
		pass

#class _jRepo

