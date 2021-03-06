###############################################################################
#
#    Copyright 2009-2011, Universitat Pompeu Fabra
#
#    This file is part of Wok.
#
#    Wok is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Wok is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses
#
###############################################################################

try:
	from lxml import etree
except ImportError:
	try:
		# Python 2.5
		import xml.etree.cElementTree as etree
	except ImportError:
		try:
			# Python 2.5+
			import xml.etree.ElementTree as etree
		except ImportError:
			try:
				# normal cElementTree install
				import cElementTree as etree
			except ImportError:
				try:
					# normal ElementTree install
					import elementtree.ElementTree as etree
				except ImportError:
					import sys
					sys.stderr.write("Failed to import ElementTree from any known place\n")
					raise

from wok.element import DataElement, dataelement_from_xml
from wok.flow.model import *

def str_to_bool(s):
	s2b = {
		"0" : False, "1" : True,
		"no" : False, "yes" : True,
		"false" : False, "true" : True}
	if s in s2b:
		return s2b[s]
	else:
		return False

class FlowReader(object):
	def __init__(self, path):
		if isinstance(path, str):
			self.fp = open(path, "r")
		else:
			self.fp = path
	
	def read(self):
		doc = etree.parse(self.fp)
		root = doc.getroot()		
		flow = self.parse_flow(root)
		return flow
		
	def parse_flow(self, root):
		if root.tag != "flow":
			raise Exception("<flow> tag not found")
			
		if "name" not in root.attrib:
			raise Exception("'name' attribute not found for tag <flow>")
		
		name = root.attrib["name"]

		title = root.findall("title")
		if len(title) == 0:
			title = name
		elif len(title) == 1:
			title = title[0].text
		elif len(title) > 1:
			raise Exception("More than one <title> found")
		
		flow = Flow(name = name, title = title)

		if "serializer" in root.attrib:
			flow.serializer = root.attrib["serializer"]

		for e in root.findall("in"):
			flow.add_in_port(self.parse_port(e))
		
		for e in root.findall("out"):
			flow.add_out_port(self.parse_port(e))

		for e in root.findall("module"):
			flow.add_module(self.parse_module(e))
		
		return flow
		
	def parse_port(self, e):
		attr = e.attrib
		
		if "name" not in attr:
			raise Exception("'name' attribute not found for tag <%s>" % e.tag)
		
		if e.tag == "in":
			ptype = PORT_TYPE_IN
		elif e.tag == "out":
			ptype = PORT_TYPE_OUT
		else:
			raise Exception("Unexpected port type: %s" % e.tag)
			
		port = Port(name = attr["name"], ptype = ptype)
		
		if "link" in attr:
			link = [x.strip() for x in e.attrib["link"].split(",")]
			if len(link) != 1 or len(link[0]) != 0:
				port.link = link
		
		if "wsize" in attr:
			port.wsize = int(attr["wsize"])
			if port.wsize < 1:
				raise Exception("At port %s: 'wsize' should be a number greater than 0" % port.name)

		if "serializer" in attr:
			port.serializer = attr["serializer"]

		return port

	def parse_module(self, e):
		attr = e.attrib
		
		if "name" not in attr:
			raise Exception("'name' attribute not found for tag <%s>" % e.tag)
		
		mod = Module(name = attr["name"])
		
		if "maxpar" in attr:
			mod.maxpar = int(attr["maxpar"])
			if mod.maxpar < 1:
				raise Exception("'maxpar' should be an integer greater or equal to 1 for module %s" % mod.name)

		if "wsize" in attr:
			mod.wsize = int(attr["wsize"])
			if mod.wsize < 1:
				raise Exception("At module %s: 'wsize' should be a number greater than 0" % mod.name)

		if "enabled" in attr:
			mod.enabled = str_to_bool(attr["enabled"])

		if "depends" in attr:
			depends = attr["depends"].split(",")
			if len(depends) != 1 or len(depends[0]) != 0:
				mod.depends = [d.strip() for d in depends]

		if "serializer" in attr:
			mod.serializer = attr["serializer"]

		for ep in e.findall("in"):
			mod.add_in_port(self.parse_port(ep))
		
		for ep in e.findall("out"):
			mod.add_out_port(self.parse_port(ep))

		mod.conf = DataElement()
		for el in e.findall("conf"):
			mod.conf.merge(self.parse_conf(el))

		exec_xml = e.find("exec")
		if exec_xml is None:
			run_xml = e.find("run")
			if run_xml is None:
				raise Exception("Missing either <exec> or <run> in module {}".format(mod.name))
			else:
				mod.execution = self._parse_run(mod, run_xml)
		else:
			mod.execution = self._parse_exec(exec_xml)

#		el = e.xpath("exec")
#		if len(el) == 0:
#			raise Exception("Missing <exec> in module %s" % mod.name)
#		elif len(el) == 1:
#			mod.execution = self.parse_exec(el[0])
#		elif len(el) > 1:
#			raise Exception("More than one <exec> found in module %s" % mod.name)

		return mod

	def parse_conf(self, e):
		return dataelement_from_xml(e)

	def _parse_exec(self, e):
		attr = e.attrib
		
		execution = Exec()
		
		if "launcher" in attr:
			execution.launcher = attr["launcher"]

		execution.conf = dataelement_from_xml(e)

		from wok import logger
		logger.initialize()
		log = logger.get_logger(name = "flow")
		msg = ""

		if "script" in execution.conf:
			msg = " Use <run>{}</run> instead".format(execution.conf["script"])

		log.warn("<exec> tag has been deprecated !" + msg)

		return execution

	def _parse_run(self, mod, xmle):
		if xmle.text is None or len(xmle.text) == 0:
			raise Exception("Missing script name for <run> in module {}".format(mod.name))

		execution = Exec()
		execution.launcher = "python"
		execution.conf = DataElement()
		execution.conf["script"] = xmle.text

		return execution

	def close(self):
		self.fp.close()
