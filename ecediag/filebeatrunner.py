from distutils.version import StrictVersion
from subprocess import run, PIPE
import logging
import os
import re

from ecediag.basicconfig import config


log = logging.getLogger(__name__)

fbexe       = config.get("ECE_DIAG","filebeatExePath")
script_dir  = config.get("PATHS", "script_dir")
fbconfig    = config.get("PATHS", "fbconfig")
diag_dir    = config.get("PATHS", "diag_dir")


def Run():
    print("Starting Filebeat")
    log.info("Running filebeat")
    fb_cmd = [
        fbexe,
        "--path.config",
        script_dir,
        "-c",
        fbconfig,
        # "--path.logs",
        # diag_dir,
        # "-e",
        "-once"
    ]
    p = run(fb_cmd, stdout=PIPE, stderr=PIPE)
    if p.returncode != 0:
        print(p.stdout.decode())
        print(p.stderr.decode())
    # print(p.stdout)
