from glob import glob
import logging

import yaml
import os

log = logging.getLogger(__name__)

class Config():

    def __init__( self, fb_cfg_path ):
        self.fb_cfg_path = fb_cfg_path
        self.yaml = self.loadFilebeatConfig()
        self.registryFile = self.GetRegistryFile()
        self.filePaths = self.GetFilePaths()
        self.registryExists = self.CheckRegistryFile()


    def loadFilebeatConfig(self):
        # print(self.fb_cfg)
        with open(self.fb_cfg_path, "r") as stream:
            try:
                data = yaml.safe_load(stream)
            except yaml.YAMLError as exc:
                print(exc)
        return data


    def GetRegistryFile(self):
        return self.yaml["filebeat.registry_file"].replace("${PWD}/","")


    def CheckRegistryFile(self):
        path = self.registryFile
        if os.path.exists(path):
            return True


    def GetFilePaths(self):
            # def _getFiles(self):
        config = self.yaml
        # print(fb_config.config)
        files = list()
        for item in config["filebeat.inputs"]:
            for path in item["paths"]:
                path = path.replace("${PWD}", os.getcwd())
                files.extend(glob(path))
        return files
