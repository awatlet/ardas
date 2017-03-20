__author__ = 'su530201'

import pysftp as sftp

try:
    s = sftp.Connection(host='xxx', username='xxx', password='xxx')
    remote_path='/home/karag/raw.dat.gz'
    local_path='/home/su530201/raw.dat.gz'
    s.get(remote_path, local_path)
    print('file transferred !')
except Exception as error:
    print('Error :' + str(error))
