from distutils.version import StrictVersion
from subprocess import run, PIPE
import logging
import os
import re

from ecediag.basicconfig import config


log = logging.getLogger(__name__)

fbexe       = config.get('ECE_DIAG','filebeatExePath')
script_dir  = config.get('PATHS', 'script_dir')
fbconfig    = config.get('PATHS', 'fbconfig')


def Run():
    log.info("Starting filebeat")
    fb_cmd = [
        fbexe,
        '-c',
        fbconfig,
        '-e',
        '-once'
    ]
    p = run(fb_cmd, stdout=PIPE)
    print(p.stdout)
