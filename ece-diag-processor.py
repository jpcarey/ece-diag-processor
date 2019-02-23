import logging
import sys
import os

from ecediag.basicconfig import config
from ecediag import securesettings
from ecediag import filebeatregistry
from ecediag import filebeatrunner
from ecediag import resourcemgr
from ecediag import cloudcontroller


if __name__ == "__main__":
    try:

        # logger = log.setup_custom_logger('root')
        # logger.debug('main message')
        os.makedirs('ecediag', exist_ok=True)
        logging.basicConfig(
            # stream=sys.stdout,
            level=logging.DEBUG,
            format="[%(asctime)s] {%(filename)s:%(lineno)d} %(levelname)s - %(message)s",
            filename='ecediag/ecediag.log',
            filemode='w'
            )

        log = logging.getLogger(__name__)
        # log.setLevel(config.get("ECE_DIAG", "LogLevel"))

        cloudcontroller.createCloud()

        # TODO: need to fix yaml loading to explode keys that contain dots.

        # init filebeat registry
        # reg = filebeatregistry.Registry(days=32)
        reg = filebeatregistry.Registry(days=30)

        fb_registry = reg.FilebeatConfig["filebeat.registry_file"].replace("${PWD}/","")
        if not os.path.exists(fb_registry):
            log.info("No existing filebeat registry, creating a new registry file")
            reg.NewRegistry(fb_registry)

        resourcemgr.load()

        filebeatrunner.Run()

    except KeyboardInterrupt:
        print("Interrupted")
