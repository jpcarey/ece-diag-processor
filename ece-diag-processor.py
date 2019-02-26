import threading
import logging
import sys
import os

from ecediag.basicconfig import config
from ecediag import securesettings
from ecediag import filebeatcontroller
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
        resourcemgr.load()

        # TODO: need to fix yaml loading to explode keys that contain dots.
        filebeatcontroller.init()

    except KeyboardInterrupt:
        sys.exit("Interrupted")
        # print("Interrupted")
