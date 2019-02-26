from subprocess import Popen, PIPE
import logging
import time
import sys

from ecediag.basicconfig import config
from ecediag import filebeatconfig
from ecediag import filebeatregistry


log = logging.getLogger(__name__)


fbexe       = config.get("ECE_DIAG","filebeatExePath")
script_dir  = config.get("PATHS", "script_dir")
fbconfig    = config.get("PATHS", "fbconfig")
diag_dir    = config.get("PATHS", "diag_dir")


def init():
    config = filebeatconfig.Config(fbconfig)
    reg = filebeatregistry.Registry(config)

    if config.registryExists:
        # print("Reading existing filebeat registry file")
        log.info("Reading existing filebeat registry file")
        reg.readFullRegistry()
    else:
        # print("No existing filebeat registry, creating a new registry file")
        log.info("No existing filebeat registry, creating a new registry file")
        # TODO: Date filter by default, allow arg to override
        reg.newRegistry(days=35)

    TOTAL = reg.total_bytes
    START = reg.readRegistryStatus()

    fb_cmd = [
        fbexe,
        "--path.config",
        script_dir,
        "-c",
        fbconfig,
        "-once"
    ]

    try:
        p = Popen(fb_cmd, stdout=PIPE, stderr=PIPE)
        while p.poll() == None:
            current = reg.readRegistryStatus()
            if not TOTAL == current:
                statusMsg = 'Filebeat upload status: {} / {}'.format(
                    sizeof_fmt(current - START),
                    sizeof_fmt(TOTAL - START)
                    )
                progress(current - START, TOTAL - START, status=statusMsg)
            time.sleep(5)

        stdout, stderr = p.communicate()
        if p.returncode != 0:
            print(stdout.decode())
            print(stderr.decode())
        else:
            sys.stdout.write("\033[F") #back to previous line
            sys.stdout.write("\033[K") #clear line
            print("✔ Finished Filebeat")
    except KeyboardInterrupt:
        print("terminating filebeat...")
        # Terminate does not actually work. Had to use kill. This seems wrong
        #  need to look into later.
        # p.terminate()
        # p.wait()
        p.kill()
        p.wait()
    except:
        print ("Unexpected error:", sys.exc_info()[0])
        raise


def progress(count, total, status=''):
    barSize = 60
    filled_len = int(round(barSize * count / float(total)))
    fillSize = int(round(barSize * count / float(total)))

    percent = round(100.0 * count / float(total), 1)
    bar = '{0}{1}'.format(
        '=' * fillSize,
        '-' * (barSize - fillSize)
        )

    sys.stdout.write('[{0}] {1}% ...{2}\r'.format(bar, percent, status))
    sys.stdout.flush()


def sizeof_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)
