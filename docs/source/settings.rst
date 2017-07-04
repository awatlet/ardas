Settings
========


``DATABASE``
------------

InfluxDB is used. ::

    DATABASE = {
        'HOST': '127.0.0.1',
        'PORT': 8086,
        'USER': 'mydatabaseuser',
        'PASSWORD': 'mypassword',
        'NAME': 'mydatabase'
    }

``ARDAS``
---------

::

    ARDAS_CONFIG = {
        'station': '0002',
        'net_id': '001',
        'integration_period': '0001'
    }


``SFTP``
--------

::

    SFTP = {
        'host': '127.0.0.1',
        'username': 'pi',
        'password': '',
        'local_path':'/home/username/test.txt',
        'remote_path': '/home/pi/remote/test.txt'
    }

