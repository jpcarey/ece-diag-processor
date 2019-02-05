from distutils.version import StrictVersion
from subprocess import run, PIPE
from glob import glob
import urllib.parse
import json
import os
import re
import requests
import base64


MIN_FB_VERSION = '6.5.4'
SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
KEYSTORE = dict()

es_configs = (
    'pipeline.ece-main.json',
    'pipeline.ece-json.json',
    'pipeline.ece-services.json',
    'pipeline.ece-zookeeper.json',
    'pipeline.elasticsearch.json',
    'pipeline.ece-dockerInspect.json',
    'template.ece.json',
    'template.ece.proxy.json',
    'template.ece.docker.inspect.json'
)

def find_filebeat():

    def is_exe(fpath):
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    def compare_version(version):
        return StrictVersion(version) >= StrictVersion(MIN_FB_VERSION)

    if "FB_PATH" in os.environ:
        fb_path = os.environ['FB_PATH']
    else:
        fb_path = input('Enter the path to Filebeat: ')

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
    fb_dir = os.path.dirname(fb_bin)
    keystore = os.path.join(fb_dir, 'filebeat.keystore')
    print(keystore)
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
    KEYSTORE = keystore

def load_es_configs(confs):
    def es_put_settings(file):
        s_file = os.path.join(SCRIPT_DIR, file)

        with open(s_file) as f:
            action = f.readline()
            data = f.read()
        request_type,request_path = action.split()
        payload = json.loads(data)

        base_url = KEYSTORE['ES_URL']
        url = urllib.parse.urljoin(base_url, request_path)
        auth = (KEYSTORE['ES_USER'], KEYSTORE['ES_PASS'])

        # r = requests.put(url, json=payload, auth=auth)
        r = requests.request(request_type, url, json=payload, auth=auth)
        r.raise_for_status()
        print("{}: {}".format(file, r.json()))

    for item in confs:
        es_put_settings(item)

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
    fb = find_filebeat()
    load_secure_setting(fb)
    load_es_configs(es_configs)
    run_filebeat(fb)
