#/usr/bin/env python3
from enum import Enum

class errorEnum(Enum):
	NO_ERROR=0
	ALREADY_PRESENT=1
	NOT_FOUND=2
	MALFORMED=3
	PERMISSIONS=4
	FILE_NOT_FOUND=5
	UPDATE_FAILED=6
	URL_IS_EMPTY=7
	URL_NOT_FOUND=8
	FILE_WRITE=9
	FILE_READ=10
	YAML_WRITE=11
	YAML_READ=12
	ADD_FAILED=13
	CONNECTION_FAIL=14

	@classmethod
	def toText(self):
		return(self.name)
	#def toText

	@classmethod
	def toInt(self):
		return(Self.value)

	@property
	def message(self) -> str:
		if hasattr(self,"msg"):
			return(self.msg)

	@message.setter
	def message(self,msg) -> None:
		self.msg=msg
#class errorEnum
