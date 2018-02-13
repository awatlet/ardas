import subprocess
import os


def get_version():
    """ Get the current version from git info

    :return: a string foramted as branch_name | last_named_tag-number_of_commits_ahead-commit_number
    """
    dir = os.path.dirname(__file__)
    branch = subprocess.check_output('cd ' + dir + '; git rev-parse --abbrev-ref HEAD', shell=True)
    version = subprocess.check_output('cd ' + dir + '; git describe --long --dirty --abbrev=6 --tags', shell=True)
    return branch.decode('ascii')[:-1] + ' | ' + version.decode('ascii')[:-1]

if __name__ == '__main__':
    print(get_version())