from subprocess import run, PIPE
import logging
import base64
import json
import os

from ecediag import filebeatvalidator
from ecediag.basicconfig import config
from ecediag.utils import exe

log = logging.getLogger(__name__)

MIN_FB_VERSION = "6.5.4"


fbexe       = config.get("ECE_DIAG","filebeatExePath")
script_dir  = config.get("PATHS", "script_dir")
fbconfig    = config.get("PATHS", "fbconfig")
fb_dir      = os.path.dirname(config.get("ECE_DIAG", "filebeatExePath"))

local_bin = os.path.join(script_dir,"bin")
beatsKeystore = exe.find_exe("beats-keystore",add_paths=[local_bin])

def load(beatsKeystoreExe=beatsKeystore):
    filebeatvalidator.validate(fbexe, MIN_FB_VERSION)
    keystore = os.path.join(script_dir, "filebeat.keystore")
    log.info("Loading Secure Settings: {}".format(keystore))


    if beatsKeystore:
        # TODO: Check if keystore exists?
        fb_cmd = [ beatsKeystoreExe, "-f", keystore ]
        p = run(fb_cmd, stdout=PIPE)

        d = json.loads(p.stdout)

        # fix structure and base64 decode values
        keystore = dict()
        for key, value in d.items():
            keystore[key] = base64.b64decode(value["value"]).decode("utf-8")

        config.set("CLUSTER", "es_url", keystore["ES_URL"])
        config.set("CLUSTER", "es_user", keystore["ES_USER"])
        config.set("CLUSTER", "es_pass", keystore["ES_PASS"])
        config.set("CLUSTER", "kb_url", keystore["KB_URL"])

    else:
        sys.exit("beats-keystore executable not available on $PATH")


def addKeystoreItem(key,item):
    log.debug("Adding to keystore: {}".format(key))

    config.set("CLUSTER", key.lower(), item)

    keystoreCmd = [
        fbexe,
        "--path.config",
        script_dir,
        "-c",
        fbconfig,
        "keystore",
        "add",
        key,
        "--stdin",
        "--force"
        ]
    # print(" ".join(keystoreCmd))
    p = run(keystoreCmd, input=item, encoding='ascii', stdout=PIPE)
    if p.returncode == 0:
        log.info('{}: {}'.format(key, p.stdout.strip()))
