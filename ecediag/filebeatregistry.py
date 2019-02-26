from timeit import default_timer as timer
from datetime import datetime, timedelta
import logging
import json
import os
import re

from ecediag.basicconfig import config


log = logging.getLogger(__name__)


class Registry():

    def __init__(self, fbconfig):
        self.fbconfig = fbconfig
        self.files = self.fbconfig.filePaths
        self.Now = datetime.utcnow()
        self.FileSet = list()


    def newRegistry(self, days=30):
        regFile = self.fbconfig.registryFile
        self.days = days
        self.dateCutoff = (datetime.today() - timedelta(days=self.days)).date()
        # self._getFiles()
        if self.days == -1:
            pass
        else:
            print("filtering data")
            self._filterData()

        # Write new filebeat registry
        entries = [ entry.filebeatRegistryFormat(self.Now) for entry in self.FileSet ]
        with open(regFile, "x") as outfile:
            json.dump(entries, outfile, separators=(",",":"))

        self._getTotal()


    def readRegistryStatus(self):
        regFile = self.fbconfig.registryFile
        with open(regFile, "r") as infile:
            data = json.load(infile)
        return sum([file["offset"] for file in data])


    def readFullRegistry(self):
        regFile = self.fbconfig.registryFile
        with open(regFile, "r") as infile:
            data = json.load(infile)
        self.files = [file["source"] for file in data]
        for file in self.files:
            entry = RegistryEntry(file)
            self.FileSet.append(entry)
        self._getTotal()

    def _filterData(self):
        for file in self.files:
            entry = RegistryEntry(file)
            entry.lineDateFilter(self.dateCutoff)
            self.FileSet.append(entry)


    def _getTotal(self):
        total = sum([entry.stat.st_size for entry in self.FileSet])
        self.total_bytes = total


class RegistryEntry():

    lineDateRegex = re.compile("^\[?(\d{4}-\d{2}-\d{2})")

    def __init__(self, file):

        self.filepath = file
        self.filename = os.path.basename(self.filepath)
        self.stat = os.stat(self.filepath)

        self.ingest = None
        self.offset = 0
        # self._lineDateFilter(file)


    def filebeatRegistryFormat(self, timestamp):
        ts = lambda t: "{}.{}{}".format(
                t.strftime("%Y-%m-%dT%H:%M:%S"),
                str(t.microsecond).ljust(9, "0"),
                "-00:00")

        return {
            "source": self.filepath,
            "offset": self.offset,
            # "timestamp": "2019-01-31T13:22:22.040722562-07:00",
            "timestamp": ts(timestamp),
            "ttl": -2,
            "type": "log",
            "meta": None,
            "FileStateOS": {
                "inode": self.stat.st_ino,
                "device": self.stat.st_dev
            }
        }


    def lineDateFilter(self, dateCutoff):

        def getFirstAndLastLine(filepath):
            offset = -10
            with open(filepath, "rb") as f:
                first_line = f.readline()
                while True:
                    f.seek(offset, os.SEEK_END)
                    lines = f.readlines()
                    if len(lines) >= 2:
                        return (first_line, lines[-1][:-1])
                    offset *= 2

        def lineCheck(line):
            if not isinstance(line, str):
                line = line.decode()
            m = re.search(self.lineDateRegex, line)
            if m:
                line_date = datetime.strptime(m.group(1),"%Y-%M-%d").date()
                # if line_date >= self.dateCutoff:
                #     return True
                return True if line_date >= dateCutoff else False

        def iterateLines(file):
            ReadFile = None
            with open(file, "r") as f:
                line = f.readline()
                position = 0

                while line:
                    line = f.readline()
                    if lineCheck(line):
                        ReadFile = True
                        offset = position
                        break
                    position = f.tell()
            self.offset = self.stat.st_size
            log.debug("size: {}, offset: {}, file: {}".format(
                self.stat.st_size, offset, file ))


        # start = timer()
        if self.stat.st_size > 0:
            firstLine, lastLine = getFirstAndLastLine(self.filepath)
            lastLineCheck = lineCheck(lastLine)
            if lastLineCheck:
                if lineCheck(firstLine):
                    self.ingest = True
                    # print("No need to scan, the full file needs to be processed".format(file))
                    # print()
                else:
                    self.ingest = True
                    # print("SCAN: {}".format(file))
                    iterateLines(self.filepath)
                    # print()
            elif lastLineCheck == False:
                self.ingest = False
                self.offset = self.stat.st_size
                # print("The file is too old: {}".format(file))
                # print()
            elif lastLineCheck == None:
                firstLineCheck = lineCheck(firstLine)
                if firstLineCheck:
                    pass
                    # print("First line matched up, but last line did not, weird. {}".format(file))
                    # print()
                elif firstLineCheck == False:
                    self.ingest = False
                    self.offset = self.stat.st_size
                    # print("Date matched, but too old {}".format(file))
                    # print()
                else:
                    if firstLine.decode("utf-8").startswith("{") and lastLine.decode("utf-8").startswith("{"):
                        pass
                        # print("probably JSON: {}".format(file))
                        # print()
                    else:
                        pass
                        # print("First and Last line did not match a date, WTF... {}".format(file))
                        # print()

        # end = timer()
        # print(end - start)
