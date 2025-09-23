#/usr/bin/env python3
import os,sys,shutil
import yaml
try:
	from .errorcode import errorEnum
except:
	from errorcode import errorEnum

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
			rawLines={}
			frepo=serial.get("file")
			lines=yaml.dump(serial)
			serial.pop("info")
			if isinstance(serial["Suites"],list):
				suites=" ".join(serial["Suites"])
			else:
				suites=serial["Suites"]
				serial["Suites"]=serial["Suites"].split(" ")
			for suite in serial["Suites"]:
				line=serial["Types"]
				if serial.get("Enabled",True)==False:
					line="#{}".format(line)
				else:
					line=line.replace("#","")
				if serial.get("Signed-By","")!="":
					line+=" [Signed-By={}]".format(serial["Signed-By"].replace("\"","").replace("\'",""))
				else:
					line+=" [Trusted=yes]"
				line+=" {}".format(serial["URIs"])
				line+=" {}".format(suite)
				line+=" {}".format(serial["Components"])
				rawLine=list(filter(None,line.strip().replace("#","").split(" ")))
				rawLine.sort()
				rawLine="".join(rawLine)
				rawLines[rawLine]=line
			if os.path.exists(frepo):
				fcontent=""
				with open(frepo,"r") as f:
					fcontent=f.read()
				dictlines={}
				for l in fcontent.split("\n"):
					if serial["URIs"] in l:
						if serial.get("Enabled",True)==False:
							if l.strip().startswith("#")==False:
								l="#{}".format(l)
						else:
							if l.strip().startswith("#")==True:
								l.lstrip("#")
					line=list(filter(None,l.strip().replace("#","").replace("\"","").replace("\'","").split(" ")))
					line.sort()
					line="".join(line)
					dictlines[line]=l
				dictlines.update(rawLines)
			else:
				dictlines=rawLines.copy()
			lines=""
			for key,line in dictlines.items():
				if len(line)==0:
					continue
				lines+="{}\n".format(line)
			lines.rstrip()
			return(lines)
	#def _generateLinesFromSerial

	def writeToFile(self):
		error=errorEnum.NO_ERROR
		serial=self.serialize()
		frepo=serial.get("file")
		if serial["Signed-By"]=="":
			serial.pop("Signed-By")
			serial["Trusted"]="yes"
		if isinstance(serial["Components"],list):
			serial["Components"]=" ".join(serial["Components"])
		if serial["format"]=="sources":
			format=serial.pop("format")
			serial["Suites"]=" ".join(serial["Suites"])
			serial.pop("file")
			serial.pop("info")
			lines=yaml.dump(serial)
			if "Trusted" in serial.keys():
				lines=lines.replace("\'yes\'","yes")
		else:
			lines=self._generateLinesFromSerial(serial)

		try:
			with open(frepo,"w") as f:
				f.write(lines)
		except Exception as e:
			error=errorEnum.FILE_WRITE
			error.message=("{}".format(e))
		return(error)
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
		error=errorEnum.NO_ERROR
		self.file=fName
		if os.path.exists(fName):
			try:
				with open(fName,"r") as f:
					fcontent=f.read()
			except Exception as e:
				error=errorEnum.FILE_READ
				error.message=("{}".format(e))
			finally:
				self.raw=fcontent
		return(error)
	#def setFile

	def getRepoDEB822(self):
		repos={}
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
			if len(line)<4:
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
			if ":/" not in repo.uri:
				continue
			repo.suites.append(line[2].strip())
			components=line[3:]
			repo.components.extend(components)
			repo.components=list(set(repo.components))
			#Process extradata
			if len(data)>0:
				dataF=data.replace("[","").replace("]","").split(",")
				for data in dataF:
					for field in data.split(" "):
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
				repos[repo.uri]["file"]=self.file
				if len(repo.signed)>0:
					repos[repo.uri]["Signed-By"]=repo.signed
				if repo.enabled==True:
					repos[repo.uri]["Enabled"]=True
			else:
				repos[repo.uri]=repo.serialize()
				repos[repo.uri]["file"]=self.file
		return(repos)
	#def _loadFromList

	def _loadFromSources(self):
		repo={}
		try:
			yFile=yaml.safe_load(self.raw)
		except Exception as e:
			raw=[]
			for line in self.raw.split("\n"):
				if ":" in line:
					line="{}: {}".format(line.strip().split(":",1)[0],line.strip().split(":",1)[-1])
					raw.append(line)
			try:
				yFile=yaml.safe_load("\n".join(raw))
			except:
				error=errorEnum.YAML_READ
				error.message=("{}".format(e))
				return({})
		finally:
			if "Enabled" not in yFile.keys():
				yFile["Enabled"]=True
			yFile["file"]=self.file
			if yFile.get("Name","")=="":
				yFile["Name"]="{}_{}".format(yFile["URIs"].rstrip("/").split("/")[-2],yFile["URIs"].rstrip("/").split("/")[-1])
			yFile["format"]="sources"
			fields=["Components","Suites"]
			for f in fields:
				yFile[f]=yFile.get(f,"").split()
				yFile[f].sort()
			repo={yFile["URIs"]:yFile.copy()}
		return(repo)
	#def _loadFromSources

	def loadFromData(self,data):
		repo=_jRepo()
		repo.file=data.get("file",self.file)
		repo.type=data["Types"]
		repo.name=data["Name"]
		repo.desc=data.get("Description","")
		repo.components=data["Components"]
		repo.suites=data["Suites"]
		repo.signed=data.get("Signed-By","")
		repo.uri=data["URIs"]
		repo.format=data["format"]
		repo.enabled=data["Enabled"]
		return(repo)
	#def loadFromData

	def writeFromData(self,data):
		repo=self.loadFromData(data)
		return(repo.writeToFile())
	#def _loadFromData

	def _writeRepoSources(self):
		pass

#class _jRepo

