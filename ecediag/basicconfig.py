from glob import glob
import configparser
import readline
import logging
import sys
import os


log = logging.getLogger(__name__)

MIN_FB_VERSION = "6.5.4"


def __LoadConfig(config):
    # TODO: figure out how to get a proper path to the root project
    script_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    settings_file = os.path.join(script_dir,"settings.ini")

    def promptFilebeatPath(message):

        readline.set_completer_delims('\t')
        readline.parse_and_bind("tab: complete")
        readline.set_completer(complete)
        fb_path = input(message)

        # fb_path = input(message)
        fb_path = os.path.expanduser(fb_path)
        if isExe(fb_path):
            return fb_path
        else:
            sys.stderr.write("Could not load filebeat, exiting")
            sys.exit(1)

    def complete(text, state):
        text = os.path.expanduser(text)
        return (glob(text+'*')+[None])[state]

    def isExe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    def createNewSettings(c):
        c["ECE_DIAG"]["filebeatExePath"] = promptFilebeatPath(
                                                "Enter the path to Filebeat: ")

        with open(settings_file, "w") as configfile:
          config.write(configfile)
        log.info("Creating a new file: {}".format(settings_file))

    def mergeDevSettings(c):
        c["ECE_DIAG"] = {**c["ECE_DIAG"], **c["DEV"]}

    def loadEnvSettings(c):
        for key, value in c.items("ECE_DIAG"):
            if key in os.environ:
                envValue = os.environ[key]
                log.info("Loading from Env: {}:{}".format(key,envValue))
                c["ECE_DIAG"][key] = envValue


    try:
    # if os.path.isfile(settings_file):
        with open(settings_file, "r") as sf:
            config.read_file(sf)
        log.debug("Reading an EXISTING FILE: {}".format(settings_file))

        if config.get("ECE_DIAG", "filebeatExePath") == "":
            raise ValueError

        if "DEV" in config:
            mergeDevSettings(config)

        loadEnvSettings(config)
    except (FileNotFoundError, ValueError):
        print("Creating new settings.ini file")
        createNewSettings(config)

    # runtime config items
    config.add_section("CLUSTER")
    config.add_section("PATHS")
    config.set("PATHS", "script_dir", script_dir)
    config.set("PATHS", "diag_dir", os.getcwd())

    fbconfig = os.path.join(
                    script_dir,
                    "resources/filebeat",
                    "filebeat-ece-diag.yml"
                    )
    config.set("PATHS", "fbconfig", fbconfig)

#########

try:
    config = configparser.ConfigParser()
    config.optionxform=str


    if not config.has_option("ECE_DIAG", "filebeatExePath"):
        # DEFAULT Config
        config["ECE_DIAG"] = {
            "filebeatExePath": "",
            "LogLevel": "INFO",
            "CloudUser": ""
            }
        __LoadConfig(config)
except KeyboardInterrupt:
    sys.exit("Interrupted")
