import subprocess
import os


def get_version():
    dir = os.path.dirname(__file__)
    branch = subprocess.check_output('cd ' + dir + '; git rev-parse --abbrev-ref HEAD', shell=True)
    version = subprocess.check_output('cd ' + dir + '; git describe --long --dirty --abbrev=7 --tags', shell=True)
    return branch.decode('ascii')[:-1] + ' | ' + version.decode('ascii')[:-1]

if __name__ == '__main__':
    print(get_version())