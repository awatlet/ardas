import sys
import logging
import pysftp as sftp
from ardas.settings import SFTP


def download_from_remote():
    if len(sys.argv) > 1:
        remote_path = sys.argv[1]
        local_path = sys.argv[2]
    else:
        logging.error('*** Arguments should be REMOTEPATH LOCALPATH')
        sys.exit(1)
    try:
        s = sftp.Connection(host=SFTP['host'], username=SFTP['username'], password=SFTP['password'])
        s.get(remote_path, local_path)
        print('file transferred !')
    except Exception as error:
        print('Error :' + str(error))


def upload_to_remote():
    if len(sys.argv) > 1:
        local_path = sys.argv[1]
        remote_path = sys.argv[2]
    else:
        logging.error('*** Arguments should be LOCALPATH REMOTEPATH')
        sys.exit(1)
    try:
        s = sftp.Connection(host=SFTP['host'], username=SFTP['username'], password=SFTP['password'])
        s.put(local_path, remote_path)
        print('file transferred !')
    except Exception as error:
        print('Error :' + str(error))

if __name__ == "__main__":
    upload_to_remote()
