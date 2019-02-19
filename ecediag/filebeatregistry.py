from timeit import default_timer as timer
from datetime import datetime, timedelta
from glob import glob
import json
import yaml
import os
import re


from ecediag.basicconfig import config


class Registry():

    def __init__(self, days=30):
        self.days = days
        self.fb_cfg = config.get('PATHS', 'fbconfig')
        self.dateCutoff = (datetime.today() - timedelta(days=self.days)).date()
        self.Now = datetime.utcnow()
        self.FilebeatConfig = self.loadFilebeatConfig()
        self.FileSet = list()


    def loadFilebeatConfig(self):
        with open(self.fb_cfg, 'r') as stream:
            try:
                data = yaml.load(stream)
                # print(data)
            except yaml.YAMLError as exc:
                print(exc)
        return data


    def _getFiles(self):
        self.files = list()
        for item in self.FilebeatConfig["filebeat.inputs"]:
            for path in item["paths"]:
                path = path.replace("${PWD}", os.getcwd())
                self.files.extend(glob(path))


    def _filterData(self):
        for file in self.files:
            entry = RegistryEntry(file,self.dateCutoff,self.Now)
            self.FileSet.append(entry)


    def NewRegistry(self,fb_path):
        self._getFiles()
        self._filterData()

        for entry in self.FileSet:
            entry.filebeatRegistry()

        x = [ entry.filebeatRegistry() for entry in self.FileSet ]
        with open(fb_path, "x") as f:
            json.dump(x, f, separators=(',',':'))


class RegistryEntry():

    lineDateRegex = re.compile('^\[?(\d{4}-\d{2}-\d{2})')

    def __init__(self, file, dateCutoff, timestamp):

        self.filepath = file
        self.filename = os.path.basename(self.filepath)
        self.dateCutoff = dateCutoff
        self.timestamp = timestamp
        self.ingest = None
        self.offset = None
        self._lineDateFilter(file)


    def filebeatRegistry(self):
        ts = lambda t: '{}.{}{}'.format(
                t.strftime('%Y-%m-%dT%H:%M:%S'),
                str(t.microsecond).ljust(9, '0'),
                "-00:00")

        return {
            "source": self.filepath,
            "offset": self.offset,
            # "timestamp": "2019-01-31T13:22:22.040722562-07:00",
            "timestamp": ts(self.timestamp),
            "ttl": -2,
            "type": "log",
            "meta": None,
            "FileStateOS": {
                "inode": self.stat.st_ino,
                "device": self.stat.st_dev
            }
        }


    def _lineDateFilter(self, file):

        def getLastLine(filename):
            offset = -10
            with open(filename, 'rb') as f:
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
                line_date = datetime.strptime(m.group(1),'%Y-%M-%d').date()
                # if line_date >= self.dateCutoff:
                #     return True
                return True if line_date >= self.dateCutoff else False

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
            print("size: {}, offset: {}, file: {}".format(self.stat.st_size, offset, file))

        self.stat = os.stat(file)
        # start = timer()
        firstLine, lastLine = getLastLine(file)
        lastLineCheck = lineCheck(lastLine)
        if lastLineCheck:
            if lineCheck(firstLine):
                self.ingest = True
                # print("No need to scan, the full file needs to be processed".format(file))
                # print()
            else:
                self.ingest = True
                # print("SCAN: {}".format(file))
                iterateLines(file)
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
