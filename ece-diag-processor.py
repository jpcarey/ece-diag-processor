from distutils.version import StrictVersion
from subprocess import run, Popen, PIPE
from glob import glob
import configparser
import urllib.parse
import requests
import logging
import base64
import json
import yaml
import sys
import os
import re


MIN_FB_VERSION = '6.5.4'
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
KEYSTORE = dict()
SETTINGS_FILE = os.path.join(SCRIPT_DIR,"settings.ini")


logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s'
    )


def validateFilebeat(fb_path):

    def compare_version(version):
        return StrictVersion(version) >= StrictVersion(MIN_FB_VERSION)

    p = run([fb_path, 'version'], stdout=PIPE)
    fb = str(p.stdout, 'utf-8')
    if fb.startswith('filebeat'):
        m = re.search(r'(\d\.\d\.\d)', str(p.stdout, 'utf-8'))
        if m:
            if compare_version(m.group(1)):
                return fb_path
            else:
                err =  'The filebeat executable you provided is too old.\n'
                err += '\tMinimum Required Version: {}\n'.format(MIN_FB_VERSION)
                err += '\tProvided Version:         {}\n'.format(m.group(1))

                sys.stderr.write(err)
                sys.exit(1)


def load_secure_setting(fb_bin):
    global KEYSTORE

    # TODO: Need to create a keystore, and fill in the Settings
    #   createKeystore does not currently work.
    def createKeystore():
        log.debug("CREATING KEYSTORE")
        keystoreCmd = [
            fb_bin,
            '--path.config',
            SCRIPT_DIR,
            '-c',
            'filebeat-ece-diag.yml',
            'keystore',
            'create'
            ]
        print(" ".join(keystoreCmd))
        p = run(keystoreCmd, stdin=PIPE, stdout=PIPE)
        print(p.stdout)

    fb_dir = os.path.dirname(fb_bin)
    keystore = os.path.join(fb_dir, 'filebeat.keystore')
    log.info("Loading Secure Settings: {}".format(keystore))
    # TODO: Check if keystore exists
    fb_cmd = [
        os.path.join(SCRIPT_DIR,'bin','beats-keystore'),
        '-f',
        keystore,
        ]
    p = run(fb_cmd, stdout=PIPE)

    d = json.loads(p.stdout)
    keystore = dict()
    for key, value in d.items():
        keystore[key] = base64.b64decode(value['value']).decode("utf-8")

    # if 'ES_URL' not in keystore:
    #     pass
    # elif 'ES_USER' not in keystore:
    #     pass
    # elif 'ES_PASS' not in keystore:
    #     pass
    # createKeystore()

    KEYSTORE = keystore


def load_es_configs(confs):
    def checkExistingESConfig(s, url, config):
        # response = requests.get(url)
        response = s.get(url)
        if response.ok:
            item = next(iter(response.json().values()))
            a = json.dumps(item, sort_keys=True)
            b = json.dumps(config, sort_keys=True)
            return True if a == b else False

    def es_put_settings(s, file):
        with open(file) as f:
            action = f.readline()
            data = f.read()
        request_type,request_path = action.split()
        payload = json.loads(data)

        base_url = KEYSTORE['ES_URL']
        url = urllib.parse.urljoin(base_url, request_path)
        s.auth = (KEYSTORE['ES_USER'], KEYSTORE['ES_PASS'])

        if not checkExistingESConfig(s, url, payload):
            r = s.request(request_type, url, json=payload)
            r.raise_for_status()
            log.debug("{}: {}".format(file, r.json()))
        else:
            log.debug('Skipping: {}'.format(file[len(SCRIPT_DIR):]))

    log.info("Loading files: \n\t{}".format('\n\t'.join(confs)))
    s = requests.Session()
    for item in confs:
        es_put_settings(s, item)


def run_filebeat(fb_bin):
    fb_cmd = [
        fb_bin,
        '-c',
        os.path.join(SCRIPT_DIR, 'filebeat-ece-diag.yml'),
        '-e',
        '-once'
    ]
    p = run(fb_cmd, stdout=PIPE)
    print(p.stdout)


def LoadConfig():

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

        with open(SETTINGS_FILE, 'w') as configfile:
          conf.write(configfile)
        log.info("Creating a new file: {}".format(SETTINGS_FILE))

    def mergeDevSettings(c):
        c['ECE_DIAG'] = {**c['ECE_DIAG'], **c['DEV']}

    def loadEnvSettings(c):
        for key, value in c.items('ECE_DIAG'):
            if key in os.environ:
                envValue = os.environ[key]
                log.info('Loading from Env: {}:{}'.format(key,envValue))
                c['ECE_DIAG'][key] = envValue


    conf = configparser.ConfigParser()
    conf.optionxform=str

    # DEFAULT Config
    conf['ECE_DIAG'] = {
        'filebeatExePath': '',
        'LogLevel': 'INFO',
        'CompressionLevel': '9'
        }

    try:
        with open(SETTINGS_FILE, 'r') as sf:
            conf.read_file(sf)
        log.debug("Reading an EXISTING FILE: {}".format(SETTINGS_FILE))

        if 'DEV' in conf:
            mergeDevSettings(conf)

        loadEnvSettings(conf)

    except FileNotFoundError:
        createNewSettings(conf)

    validateFilebeat(conf['ECE_DIAG']['filebeatExePath'])
    return conf


if __name__ == "__main__":
    try:
        log = logging.getLogger(__name__)
        config = LoadConfig()
        conf = config['ECE_DIAG']
        log.setLevel(conf['LogLevel'])
        fb = conf['filebeatExePath']

        load_secure_setting(fb)

        pipeline_pattern = os.path.join(SCRIPT_DIR,'ingest_pipelines/pipeline.*.json')
        template_pattern = os.path.join(SCRIPT_DIR, 'es_templates/template.*.json')
        es_configs = glob(pipeline_pattern)
        es_configs.extend(glob(template_pattern))
        load_es_configs(es_configs)

        run_filebeat(fb)
    except KeyboardInterrupt:
        print('Interrupted')
