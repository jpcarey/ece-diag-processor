from subprocess import run, PIPE
import logging
import base64
import json
import os


log = logging.getLogger(__name__)


def load(config):
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

    script_dir = config.get('PATHS', 'script_dir')
    fb_dir = os.path.dirname(config.get('ECE_DIAG', 'filebeatExePath'))
    # fb_dir = os.path.dirname(fb_bin)
    keystore = os.path.join(fb_dir, 'filebeat.keystore')
    log.info("Loading Secure Settings: {}".format(keystore))

    # TODO: Check if keystore exists
    fb_cmd = [
        os.path.join(script_dir,'bin','beats-keystore'),
        '-f',
        keystore,
        ]
    p = run(fb_cmd, stdout=PIPE)

    d = json.loads(p.stdout)

    # fix structure and base64 decode values
    keystore = dict()
    for key, value in d.items():
        keystore[key] = base64.b64decode(value['value']).decode("utf-8")

    config.add_section('CLUSTER')
    config.set('CLUSTER', 'es_url', keystore['ES_URL'])
    config.set('CLUSTER', 'es_user', keystore['ES_USER'])
    config.set('CLUSTER', 'es_pass', keystore['ES_PASS'])
