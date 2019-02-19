import configparser
import logging
import os

from ecediag import securesettings
from ecediag import filebeatvalidator


log = logging.getLogger(__name__)

MIN_FB_VERSION = '6.5.4'


def __LoadConfig(config):
    # TODO: figure out how to get a proper path to the root project
    script_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    settings_file = os.path.join(script_dir,"settings.ini")

    def promptFilebeatPath(message):
        fb_path = input(message)
        fb_path = os.path.expanduser(fb_path)
        if isExe(fb_path):
            return fb_path
        else:
            sys.stderr.write('Could not load filebeat, exiting')
            sys.exit(1)


    def isExe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    def createNewSettings(c):
        c['ECE_DIAG']['filebeatExePath'] = promptFilebeatPath(
                                                'Enter the path to Filebeat: ')

        with open(settings_file, 'w') as configfile:
          conf.write(configfile)
        log.info("Creating a new file: {}".format(settings_file))

    def mergeDevSettings(c):
        c['ECE_DIAG'] = {**c['ECE_DIAG'], **c['DEV']}

    def loadEnvSettings(c):
        for key, value in c.items('ECE_DIAG'):
            if key in os.environ:
                envValue = os.environ[key]
                log.info('Loading from Env: {}:{}'.format(key,envValue))
                c['ECE_DIAG'][key] = envValue

    try:
        with open(settings_file, 'r') as sf:
            config.read_file(sf)
        log.debug("Reading an EXISTING FILE: {}".format(settings_file))

        if 'DEV' in config:
            mergeDevSettings(config)

        loadEnvSettings(config)

    except FileNotFoundError:
        createNewSettings(config)

    config.add_section('PATHS')
    config.set('PATHS', 'script_dir', script_dir)

    fbconfig = os.path.join(
                    script_dir,
                    "resources/filebeat",
                    "filebeat-ece-diag.yml"
                    )
    config.set('PATHS', 'fbconfig', fbconfig)

    filebeatvalidator.validate(
        config.get('ECE_DIAG','filebeatExePath'),
        MIN_FB_VERSION
        )

    securesettings.load(config)

config = configparser.ConfigParser()
config.optionxform=str


if not config.has_option('ECE_DIAG', 'filebeatExePath'):
    # DEFAULT Config
    config['ECE_DIAG'] = {
        'filebeatExePath': '',
        'LogLevel': 'INFO',
        'CompressionLevel': '9'
        }
    __LoadConfig(config)
