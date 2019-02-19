import logging
import sys
import os

from ecediag.basicconfig import config
from ecediag import filebeatregistry
from ecediag import filebeatrunner
from ecediag import resourcemgr


logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s'
    )


if __name__ == "__main__":
    try:
        log = logging.getLogger(__name__)
        log.setLevel(config.get('ECE_DIAG', 'LogLevel'))

        # TODO: need to fix yaml loading to explode keys that contain dots.

        # init filebeat registry
        reg = filebeatregistry.Registry()

        fb_registry = reg.FilebeatConfig["filebeat.registry_file"].replace("${PWD}/","")
        if not os.path.exists(fb_registry):
            log.info("No existing filebeat registry, creating a new registry file")
            reg.NewRegistry(fb_registry)

        resourcemgr.load()

        filebeatrunner.Run()

    except KeyboardInterrupt:
        print('Interrupted')
