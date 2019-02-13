from distutils.version import StrictVersion
from subprocess import run, Popen, PIPE
from glob import glob
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
SETTINGS_FILE = os.path.join(SCRIPT_DIR,"settings.yml")

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    # level=logging.DEBUG,
    format='[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s'
    )

pipeline_pattern = os.path.join(SCRIPT_DIR,'ingest_pipelines/pipeline.*.json')
template_pattern = os.path.join(SCRIPT_DIR, 'es_templates/template.*.json')
es_configs = glob(pipeline_pattern)
es_configs.extend(glob(template_pattern))


def find_filebeat():

    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    def compare_version(version):
        return StrictVersion(version) >= StrictVersion(MIN_FB_VERSION)
    def load_settings():
        settings = dict()
        try:
            if os.path.isfile(SETTINGS_FILE):
                with open(SETTINGS_FILE, 'r') as f:
                    settings = yaml.safe_load(f)
            if 'filebeat_exe_path' in settings:
                return settings['filebeat_exe_path']
        except yaml.YAMLError as exc:
            print(exc)

    def store_settings(data):
        with open(SETTINGS_FILE, 'w') as outfile:
            yaml.dump(data, outfile)
    def prompt_fb_path(message):
        fb_path = input(message)
        fb_path = os.path.expanduser(fb_path)
        if is_exe(fb_path):
            s = {
                'filebeat_exe_path': fb_path
            }
            store_settings(s)
            return fb_path
        else:
            sys.stderr.write('Could not load filebeat, exiting')
            sys.exit(1)


    fb_path = load_settings()
    if "FB_PATH" in os.environ:
        fb_path = os.path.expanduser(os.environ['FB_PATH'])
    else:
        try:
            if is_exe(fb_path):
                log.debug("Loading filebeat from SETTINGS_FILE: {}".format(fb_path))
            else:
                print("The filebeat path loaded from settings did not work")
                print("Please check that {} is correct".format(fb_path))
                fb_path = prompt_fb_path('Enter the path to Filebeat: ')
        except (NameError, TypeError) as e:
            log.debug("No path to filebeat in ENV or Settings")
            fb_path = prompt_fb_path('Enter the path to Filebeat: ')

    fb_path = os.path.expanduser(fb_path)

    if is_exe(fb_path):
        p = run([fb_path, 'version'], stdout=PIPE)
        fb = str(p.stdout, 'utf-8')
        if fb.startswith('filebeat'):
            m = re.search(r'(\d\.\d\.\d)', str(p.stdout, 'utf-8'))
            if m:
                if compare_version(m.group(1)):
                    return fb_path


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
        os.path.join(SCRIPT_DIR,'decrypt_keystore'),
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


if __name__ == "__main__":
    log = logging.getLogger(__name__)
    fb = find_filebeat()
    load_secure_setting(fb)
    load_es_configs(es_configs)
    run_filebeat(fb)
