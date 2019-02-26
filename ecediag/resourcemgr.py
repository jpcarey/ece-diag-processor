from glob import glob
import urllib.parse
import requests
import logging
import json
import sys
import os

from ecediag.basicconfig import config


log = logging.getLogger(__name__)

script_dir = config.get("PATHS", "script_dir")


def load():
    print('Checking ES Ingest Pipelines and Templates', end="\r")
    pipeline_pattern = os.path.join(
        script_dir,
        "resources/es_ingest_pipelines/pipeline.*.json"
        )
    template_pattern = os.path.join(
        script_dir,
        "resources/es_templates/template.*.json"
        )

    es_configs = glob(pipeline_pattern)
    es_configs.extend(glob(template_pattern))
    loadESResources(es_configs)

    sys.stdout.write("\033[K") # clear line
    print("✔ ES Ingest Pipelines and Templates")

    print('Checking Kibana Objects', end="\r")
    kibana_objects = os.path.join(
        script_dir,
        "resources/kibana/*.json"
        )
    kb_configs = glob(kibana_objects)
    loadKibanaResources(kb_configs)
    sys.stdout.write("\033[K") # clear line
    print("✔ Kibana Objects")


def loadESResources(confs):
    log.info("Loading files: \n\t{}".format("\n\t".join(confs)))
    s = requests.Session()
    s.auth = (
        config.get("CLUSTER", "es_user"),
        config.get("CLUSTER", "es_pass")
        )

    for item in confs:
        _es_settings(s, item)


def _es_settings(s, file):
    with open(file) as f:
        action = f.readline()
        data = f.read()
    request_type,request_path = action.split()
    payload = json.loads(data)

    base_url = config.get("CLUSTER", "es_url")
    url = urllib.parse.urljoin(base_url, request_path)

    if not _checkExistingESConfig(s, url, payload):
        r = s.request(request_type, url, json=payload)
        r.raise_for_status()
        log.debug("{}: {}".format(file, r.json()))
    else:
        log.debug("Skipping: {}".format(file[len(script_dir):]))


def _checkExistingESConfig(s, url, config):
    # response = requests.get(url)
    response = s.get(url)
    if response.ok:
        item = next(iter(response.json().values()))
        a = json.dumps(item, sort_keys=True)
        b = json.dumps(config, sort_keys=True)
        return True if a == b else False


def loadKibanaResources(confs):
    log.info("Loading Kibana: \n\t{}".format("\n\t".join(confs)))
    s = requests.Session()
    s.auth = (
        config.get("CLUSTER", "es_user"),
        config.get("CLUSTER", "es_pass")
        )
    s.headers.update({'kbn-xsrf': 'true'})

    for item in confs:
        _kb_settings(s, item)


def _kb_settings(s, file):
    with open(file) as f:
        action = f.readline()
        data = f.read()
    request_type,request_path = action.split()
    payload = json.loads(data)

    base_url = config.get("CLUSTER", "kb_url")
    url = urllib.parse.urljoin(base_url, request_path)
    if os.path.basename(file) == 'default-pattern.json':
        r = s.request(request_type, url, json=payload)
    elif not _checkExistingKibanaConfig(s, url, payload):
        kb_payload = {'attributes': payload.pop('attributes')}
        r = s.request(request_type, url, json=kb_payload)
        # print(r.text)
        # print(r.status_code)
        r.raise_for_status()
        log.debug("{}: {}".format(file, r.json()))
    else:
        log.debug("Skipping: {}".format(file[len(script_dir):]))


def _checkExistingKibanaConfig(s, url, config):
    response = s.get(url)
    if response.ok:
        item = response.json()
        item = item.pop('attributes')
        config = config.pop('attributes')
        # item.pop('updated_at', None)
        # item.pop('version', None)
        a = json.dumps(item, sort_keys=True)
        b = json.dumps(config, sort_keys=True)
        return True if a == b else False
