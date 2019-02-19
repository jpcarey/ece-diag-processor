from glob import glob
import urllib.parse
import requests
import logging
import json
import os

from ecediag.basicconfig import config


log = logging.getLogger(__name__)

script_dir = config.get('PATHS', 'script_dir')


def __loadResources(confs):

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

        # base_url = KEYSTORE['ES_URL']
        base_url = config.get('CLUSTER', 'es_url')
        url = urllib.parse.urljoin(base_url, request_path)

        s.auth = (
            config.get('CLUSTER', 'es_user'),
            config.get('CLUSTER', 'es_pass')
            )

        if not checkExistingESConfig(s, url, payload):
            r = s.request(request_type, url, json=payload)
            r.raise_for_status()
            log.debug("{}: {}".format(file, r.json()))
        else:
            log.debug('Skipping: {}'.format(file[len(script_dir):]))

    log.info("Loading files: \n\t{}".format('\n\t'.join(confs)))
    s = requests.Session()
    for item in confs:
        es_put_settings(s, item)


def load():

    pipeline_pattern = os.path.join(
        script_dir,
        'resources/es_ingest_pipelines/pipeline.*.json'
        )
    template_pattern = os.path.join(
        script_dir,
        'resources/es_templates/template.*.json'
        )

    es_configs = glob(pipeline_pattern)
    es_configs.extend(glob(template_pattern))

    __loadResources(es_configs)
