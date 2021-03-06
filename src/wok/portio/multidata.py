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

from wok.portio import PortData, DataReader

TYPE_MULTI_DATA = "multi_data"

class MultiData(PortData):
	def __init__(self, sources = None, start = 0, size = -1, conf = None):
		PortData.__init__(self, None, conf)

		if conf is not None:
			self._sources = []
			from wok.portio.factory import PortDataFactory
			for sconf in conf["sources"]:
				self._sources += [PortDataFactory.create_port_data(sconf)]
			self._start = conf.get("start", start, dtype=int)
			self._size = conf.get("size", size, dtype=int)
		else:
			self._sources = sources
			self._start = start
			self._size = size

		if self._sources:
			i = 0
			serializer = None
			while i < len(self._sources) and serializer is None:
				self._serializer = self._sources[i].serializer
				i += 1

	def size(self):
		return sum([src.size() for src in self._sources])

	def fill_element(self, e):
		PortData.fill_element(self, e)
		e["type"] = TYPE_MULTI_DATA
		e["start"] = self._start
		e["size"] = self._size
		l = e.create_list()
		for src in self._sources:
			pe = e.create_element()
			l += [src.fill_element(pe)]
		e["sources"] = l
		return e
	
	def get_slice(self, start = None, size = None):
		if start is None:
			start = self._start
		if size is None:
			size = self._size

		return MultiData(self._sources, start, size)

	def reader(self):
		return MultiDataReader(self._sources, self._start, self._size)

	def __repr__(self):
		sb = ["[", ", ".join([str(x) for x in self._sources]), "]"]
		if self._start != -1:
			sb += [" ", str(self._start)]
			if self._size != -1:
				sb += [":", str(self._start + self._size - 1)]
		return "".join(sb)

class MultiDataReader(DataReader):
	def __init__(self, sources, start, size):
		DataReader.__init__(self)

		self._sources = sources
		self._start = start
		self._size = size

		self._source_index = -1
		self._source_size = 0
		self._reader = None

	def open(self):
		if not self._sources:
			raise StopIteration()

		index = 0
		src = self._sources[0]
		start = self._start
		src_size = src.size()

		while start - src_size > 0 and index < len(self._sources):
			index += 1
			src = self._sources[index]
			start -= src_size
			src_size = src.size()
			
		self._source_index = index
		src = src.get_slice(start, min(src_size - start, self._size))
		self._reader = src.reader()

	def close(self):
		if self._reader is not None:
			self._reader.close()
			self._reader = None

	def is_opened(self):
		return self._reader is not None

	def next(self):
		if self._size == 0:
			raise StopIteration()

		if self._reader is None:
			self.open()

		value = None
		while value is None:
			try:
				value = self._reader.next()
			except StopIteration:
				self._source_index += 1
				if self._source_index >= len(self._sources):
					raise StopIteration()
				src = self._sources[self._source_index]
				src = src.get_slice(0, min(src.size(), self._size))
				self._reader = src.reader()
				value = None

		self._size -= 1
		self._source_size -= 1
		
		return value

	def __repr__(self):
		sb = ["{", ", ".join([repr(s) for s in self._sources]), "}"]
		if self._start != 0 and self._size != -1:
			sb += [" %i" % self._start]
			if self._size != -1:
				sb += [":%i" % (self._start + self._size - 1)]
		return "".join(sb)
