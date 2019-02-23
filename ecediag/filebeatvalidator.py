from distutils.version import StrictVersion
from subprocess import run, PIPE
import re


def validate(fb_path, min_version):

    def compare_version(version):
        return StrictVersion(version) >= StrictVersion(min_version)

    p = run([fb_path, "version"], stdout=PIPE)
    fb = str(p.stdout, "utf-8")
    if fb.startswith("filebeat"):
        m = re.search(r"(\d\.\d\.\d)", str(p.stdout, "utf-8"))
        if m:
            if compare_version(m.group(1)):
                return fb_path
            else:
                err =  "The filebeat executable you provided is too old.\n"
                err += "\tMinimum Required Version: {}\n".format(min_version)
                err += "\tProvided Version:         {}\n".format(m.group(1))

                sys.stderr.write(err)
                sys.exit(1)
