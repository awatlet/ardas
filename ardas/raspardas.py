from binascii import crc32
import datetime
import logging
import queue
import socket
from time import gmtime, sleep
from os import path, mkdir, statvfs
from struct import unpack_from
from threading import Thread
import ntplib
import serial
from ardas.settings import DATABASE, ARDAS_CONFIG, SENSORS, MASTER_CONFIG, LOGGING_CONFIG, DATA_LOGGING_CONFIG
from influxdb import InfluxDBClient
from ardas.compressed_sized_timed_rotating_logger import CompressedSizedTimedRotatingFileHandler

version = 'v1.1.2.42'

# setup loggers
sys_logger = logging.getLogger('sys_logger')
data_logger = logging.getLogger('data_logger')
debug = LOGGING_CONFIG['debug_mode']
logging_to_console = LOGGING_CONFIG['logging_to_console']
influxdb_logging = DATA_LOGGING_CONFIG['influxdb_logging']

# Data logging setup
# Set data and message logging paths
base_path = path.dirname(__file__)
data_path = path.join(base_path, 'data')
if not path.isdir(data_path):
    mkdir(data_path)
data_log_filename = path.join(data_path, DATA_LOGGING_CONFIG['file_name'])


# Connection to master
local_host = MASTER_CONFIG['local_host']
local_port = MASTER_CONFIG['local_port']
master_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
master_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
master_connection = None
master_online = False

# Connection and communication with slave
slave_io = None
n_channels = len(SENSORS)
chunk_size = 4096
raw_data = ARDAS_CONFIG['raw_data_on_disk']

peer_download = False  # TODO: find a way to set peer_download to True if another ardas is downloading at startup
downloading = False
pause = True  # used to suspend datalogging during some operations such as start_sequence
stop = False

slave_queue = queue.Queue()  # what comes from ArDAS
master_queue = queue.Queue()  # what comes from Master (e.g. cron task running client2.py)

# Remaining initialization
status = True


def init_logging():
    global sys_logger, data_logger, logging_level, logging_to_console, data_log_filename, debug
    """ This is the init sequence for the logging system """

    # Debug and logging
    if debug:
        logging_level = sys_logger.DEBUG
    else:
        logging_level = sys_logger.INFO

    # Set data and message logging paths
    log_path = path.join(path.dirname(__file__), 'logs')
    if not path.isdir(log_path):
        mkdir(log_path)
    log_file = path.join(log_path, LOGGING_CONFIG['file_name'])

    # Set message logging format and level
    sys_logger.Formatter.converter = gmtime
    log_format = '%(asctime)-15s | %(process)d | %(levelname)s: %(message)s'
    if logging_to_console:
        sys_logger.basicConfig(format=log_format, datefmt='%Y/%m/%d %H:%M:%S UTC', level=logging_level,
                            handlers=[
                                CompressedSizedTimedRotatingFileHandler(log_file, maxBytes=LOGGING_CONFIG['max_bytes'],
                                                                        backupCount=LOGGING_CONFIG['backup_count'],
                                                                        when=LOGGING_CONFIG['when'],
                                                                        interval=LOGGING_CONFIG['interval']),
                                sys_logger.StreamHandler()]
                            )
    else:
        sys_logger.basicConfig(format=log_format, datefmt='%Y/%m/%d %H:%M:%S UTC', level=logging_level,
                            handlers=[
                                CompressedSizedTimedRotatingFileHandler(log_file, maxBytes=LOGGING_CONFIG['max_bytes'],
                                                                        backupCount=LOGGING_CONFIG['backup_count'],
                                                                        when=LOGGING_CONFIG['when'],
                                                                        interval=LOGGING_CONFIG['interval'])]
                            )
    sys_logger.info('')
    sys_logger.info('****************************')
    sys_logger.info('*** NEW SESSION STARTING ***')
    sys_logger.info('****************************')
    sys_logger.info('Raspardas version ' + version + '.')
    sys_logger.info('')
    if debug:
        sys_logger.warning('Debug mode: ON')
    sys_logger.info('Logging level: %s' % logging_level)
    try:
        st = statvfs('.')
        available_space = st.f_bavail * st.f_frsize / 1024 / 1024
        sys_logger.info('Remaining disk space : %.1f MB' % available_space)
    except:
        pass
    sys_logger.info('Saving log to ' + log_file)

    data_logger.setLevel(logging.INFO)
    handler = CompressedSizedTimedRotatingFileHandler(data_log_filename,
                                                      maxBytes=DATA_LOGGING_CONFIG['max_bytes'],
                                                      backupCount=DATA_LOGGING_CONFIG['backup_count'],
                                                      when=DATA_LOGGING_CONFIG['when'],
                                                      interval=DATA_LOGGING_CONFIG['interval'])
    data_logger.addHandler(handler)


def listen_slave():
    """This is a listener thread function.
    It processes items in the queue one after
    another.  This daemon threads runs into an
    infinite loop, and only exit when
    the main thread ends.
    """
    global stop, downloading, slave_io, data_queue, n_channels, slave_queue, master_queue, raw_data, \
        influxdb_logging, master_online, pause, data_logger

    sensors = SENSORS
    # slave_io.reset_input_buffer()
    # slave_io.reset_output_buffer()
    while not stop:
        # Read incoming data from slave (ArDAS)
        try:
            byte = b''
            msg = b''
            while byte != b'\r' and byte != b'$':
                byte = slave_io.read(1)
                msg += byte
            if byte == b'$':
                record = byte
                record += slave_io.read(32)
                crc = slave_io.read(4)
                record_crc = int.from_bytes(crc, 'big')
                msg_crc = crc32(record)
                sys_logger.debug('record : %s' % str(record))
                sys_logger.debug('record_crc : %d' % record_crc)
                sys_logger.debug('msg_crc : %d' % msg_crc)
                if msg_crc == record_crc:
                    crc_check = True
                else:
                    crc_check = False
                if crc_check:
                    instr = []
                    freq = []
                    station = int.from_bytes(record[1:3], 'big')
                    integration_period = int.from_bytes(record[3:5], 'big')
                    record_date = datetime.datetime.utcfromtimestamp(int.from_bytes(record[5:9], 'big'))
                    # record_date = record_date.replace(tzinfo=datetime.timezone.utc)
                    for i in range(n_channels):
                        instr.append(int.from_bytes(record[9+2*i:11+2*i], 'big'))
                        freq.append(unpack_from('>f', record[17+4*i:21+4*i])[0])
                    decoded_record = '%04d ' % station + record_date.strftime('%Y %m %d %H %M %S') \
                                     + ' %04d' % integration_period
                    if raw_data:
                        decoded_record += ' R'
                    else:
                        decoded_record += ' C'
                        val = [0.]*n_channels
                    for i in range(n_channels):
                        val[i] = sensors[i].output(freq[i])
                        if raw_data:
                            decoded_record += ' %04d %11.4f' % (instr[i], freq[i])
                        else:
                            decoded_record += ' %04d %11.4f' % (instr[i], val[i])
                    decoded_record += '\n'
                    sys_logger.debug('Master connected: %s' % master_online)
                    if not raw_data:
                        cal_record = '%04d ' % station + record_date.strftime('%Y %m %d %H %M %S')
                        for i in range(n_channels):
                            s = '| %04d: ' % instr[i]
                            s += sensors[i].output_repr(freq[i])
                            s += ' '
                            cal_record += s
                        cal_record += '|'
                        if not pause:
                            data_logger.info(cal_record)
                        cal_record += '\n'
                        if master_online:
                            slave_queue.put(cal_record.encode('utf-8'))
                    if influxdb_logging and not pause:
                        data = []
                        for i in range(n_channels):
                            if sensors[i].log:
                                data.append({'measurement': 'temperatures', 'tags': {'sensor': '%04d' % instr[i]},
                                             'time': record_date.strftime('%Y-%m-%d %H:%M:%S %Z'),
                                             'fields': {'value': val[i]}})
                        sys_logger.debug('Writing to InfluxDB : %s' % str(data))
                        client.write_points(data)
                else:
                    sys_logger.warning('*** Bad crc : corrupted data is not stored !')

            else:
                if len(msg) > 0:
                    try:
                        sys_logger.debug('Slave says : ' + msg.decode('ascii'))
                    except:
                        sys_logger.warning('*** listen_slave thread - Unable to decode slave message...')
                    if not downloading:
                        slave_queue.put(msg)
            sleep(0.2)
        except queue.Full:
            sys_logger.warning('*** Data or slave queue is full!')
        except serial.SerialTimeoutException:
            pass
    sys_logger.debug('Closing listen_slave thread...')


def talk_slave():
    """This is a talker thread function.
    It processes items in the queue one after
    another.  This daemon threads runs into an
    infinite loop, and only exit when
    the main thread ends.
    """
    global stop, slave_io, master_queue

    while not stop:
        try:
            msg = master_queue.get(timeout=0.25)
            try:
                sys_logger.debug('Saying to slave : ' + msg.decode('ascii'))
            except:
                sys_logger.warning('*** talk_slave thread - Unable to decode master message...')
            slave_io.write(msg)
            sys_logger.debug('In waiting: ' + str(slave_io.in_waiting))
            sys_logger.debug('Out waiting: ' + str(slave_io.out_waiting))
            #slave_io.flush()  # NOTE: this line was commented as a test
        except queue.Empty:
            pass
        except serial.SerialTimeoutException:
            sys_logger.error('*** Could not talk to slave...')

    sys_logger.debug('Closing talk_slave thread...')


def connect_master():
    """This is a connection listener thread function.
    It waits for a connection from the master.
    This daemon threads runs into an
    infinite loop, and only exit when
    the main thread ends.
    """
    global stop, master_connection, master_socket, master_online

    while not stop:
        try:
            if not master_online:
                sys_logger.info('Waiting for master...')
                master_connection, addr = master_socket.accept()
                sys_logger.info('Master connected, addr: ' + str(addr))
                master_online = True
        except:
            sys_logger.error('*** Master connection error!')

    if master_online:
        msg = b'\n*** Ending connection ***\n\n'
        master_connection.send(msg)
    master_connection.close()
    sys_logger.debug('Closing connect_master thread...')


def listen_master():
    """This is a listener thread function.
    It processes items in the queue one after
    another.  This daemon threads runs into an
    infinite loop, and only exit when
    the main thread ends.
    """
    global stop, master_connection, master_queue, master_online, raw_data, pause

    while not stop:
        if master_online:
            try:
                byte = b''
                msg = b''
                while byte != b'\r':
                    byte = master_connection.recv(1)
                    msg += byte
                if msg[0:1] == b'\n':
                    msg = msg[1:]
                if len(msg) > 0:
                    try:
                        sys_logger.debug('Master says : ' + msg.decode('ascii'))
                    except:
                        sys_logger.warning('*** listen_master thread - Unable to decode master message...')
                    if msg[:-1] == b'#XB':
                        sys_logger.info('Full download is not available')
                    elif msg[:-1] == b'#XP':
                        sys_logger.info('Partial download request')
                    elif msg[:-1] == b'#XS':
                        sys_logger.info('Aborting download request')
                    elif msg[:-1] == b'#ZF':
                        sys_logger.info('Reset request')
                    elif msg[:-1] == b'#PA':
                        if pause:
                            sys_logger.info('Resume data logging')
                        else:
                            sys_logger.info('Pause data logging')
                        pause = not pause
                    elif msg[:-1] == b'#RC':
                        raw_data = not raw_data
                        if raw_data:
                            sys_logger.info('Switching to raw data.')
                        else:
                            sys_logger.info('Switching to calibrated data.')
                    elif msg[:-1] == b'#KL':
                        sys_logger.info('Stop request')
                        stop = True
                    else:
                        master_queue.put(msg)
            except queue.Full:
                sys_logger.error('*** Master queue is full!')
            except:
                sys_logger.warning('Master connection lost...')
                master_online = False
    sys_logger.debug('Closing listen_master thread...')


def talk_master():
    """This is a talker thread function.
    It processes items in the queue one after
    another.  This daemon threads runs into an
    infinite loop, and only exit when
    the main thread ends.
    """
    global stop, downloading, master_connection, slave_queue, master_online

    while not stop:
        if master_online:
            try:
                if not downloading:
                    msg = slave_queue.get(timeout=0.25)
                    try:
                        sys_logger.debug('Saying to master :' + msg.decode('utf-8'))
                        master_connection.send(msg)
                    except:
                        sys_logger.warning('*** talk_master thread - Unable to decode slave message...')
                        master_connection.send(msg)

            except queue.Empty:
                pass
            except:
                sys_logger.warning('Master connection lost...')
                master_online = False
    sys_logger.debug('Closing talk_master thread...')


def start_sequence():
    global master_queue, slave_queue, n_channels

    sys_logger.debug('Initiating start sequence...')
    sys_logger.debug('____________________________')

    while not slave_queue.empty():
        sleep(0.01)
    sys_logger.debug('start_sequence : Wake up slave...')
    if debug:
        reply = False
        while not reply:
            msg = b'-999\r\n'  # FIX: Should be /r
            master_queue.put(msg)
            sys_logger.debug('start_sequence : Calling all ArDAS')
            msg = b''
            k = 10
            while k > 0 and not reply:  # FIX: this does not seem to work properly each time (it loops endlessly)
                try:
                    msg = slave_queue.get(timeout=0.25)
                except queue.Empty:
                    sys_logger.debug('start_sequence : Timed out...')
                if msg != b'':
                    if b'Hey!' in msg:
                        sys_logger.debug('start_sequence : Reply received!')
                        reply = True
                    else:
                        sys_logger.debug('start_sequence : No proper reply received yet...')
                else:
                    sys_logger.debug('start_sequence : No message received yet...')
                sleep(0.25)
                k -= 1
    reply = False
    while not reply:
        msg = b'-' + bytes(ARDAS_CONFIG['net_id'].encode('ascii')) + b'\r\n'  # FIX: Should be /r
        master_queue.put(msg)
        sys_logger.debug('start_sequence : Sending wake-up command')
        msg = b''
        k = 10
        while k > 0 and not reply:
            try:
                msg = slave_queue.get(timeout=0.25)
            except queue.Empty:
                sys_logger.debug('start_sequence : Timed out...')
            if msg != b'':
                if len(msg) > 3 and msg[0:4] == b'!HI ':
                    sys_logger.debug('start_sequence : Reply received!')
                    reply = True
                else:
                    sys_logger.debug('start_sequence : No proper reply received yet...')
            sleep(0.25)
            k -= 1

    reply = False
    while not reply:
        msg = b'#ZR '
        msg += bytes(ARDAS_CONFIG['station'].encode('ascii'))
        msg += b' '
        msg += bytes(ARDAS_CONFIG['net_id'].encode('ascii'))
        msg += b' '
        msg += bytes(ARDAS_CONFIG['integration_period'].encode('ascii'))
        msg += b' '
        msg += bytes(str(n_channels).encode('ascii'))
        msg += b' '
        for i in SENSORS:
            msg += bytes(i.sensor_id.encode('ascii'))
            msg += b' '
        msg += b'31\r'
        master_queue.put(msg)
        sleep(1)
        sys_logger.debug('start_sequence : Sending reconfig command')
        try:
            msg = slave_queue.get(timeout=0.25)
        except:
            pass
        if msg[0:4] == b'!ZR ':
            sys_logger.debug('start_sequence : Reply received!')
            reply = True
        else:
            sys_logger.debug('start_sequence : No proper reply received yet...')

    reply = False
    while not reply:
        msg = b'#E0\r'
        master_queue.put(msg)
        sys_logger.debug('start_sequence : Sending no echo command')
        try:
            msg = slave_queue.get(timeout=0.25)
        except:
            pass
        if msg[0:4] == b'!E0 ':
            sys_logger.debug('start_sequence : Reply received!')
            reply = True
        else:
            sys_logger.debug('start_sequence : No proper reply received yet...')
    sys_logger.debug('start_sequence : Resetting clock...')
    c = ntplib.NTPClient()
    reply = False
    while not reply:
        try:
            sys_logger.debug('start_sequence : Getting time from NTP...')
            now = datetime.datetime.utcfromtimestamp(c.request('europe.pool.ntp.org').tx_time)
            msg = '#SD %04d %02d %02d %02d %02d %02d\r' % (now.year, now.month, now.day, now.hour, now.minute, now.second)
            master_queue.put(bytes(msg.encode('ascii')))
            sys_logger.debug('start_sequence : Setting ArDAS date from NTP server: %04d %02d %02d %02d %02d %02d' %
                         (now.year, now.month, now.day, now.hour, now.minute, now.second))
            try:
                msg = slave_queue.get(timeout=0.25)
            except:
                pass
            if msg[0:4] == b'!SD ':
                sys_logger.info('start_sequence : ArDAS date set from NTP server: %04d %02d %02d %02d %02d %02d' %
                             (now.year, now.month, now.day, now.hour, now.minute, now.second))
                reply = True
            else:
                sys_logger.debug('start_sequence : No proper reply received yet...')
        except:
            sys_logger.debug('start_sequence : Unable to get date and time from to NTP !')
    sys_logger.debug('Start sequence finished...')
    sys_logger.debug('__________________________')

if __name__ == '__main__':
    init_logging()

    sys_logger.info('ArDAS settings:')
    sys_logger.info('   station: %s' % ARDAS_CONFIG['station'])
    sys_logger.info('   net ID: %s' % ARDAS_CONFIG['net_id'])
    sys_logger.info('   integration period: %s' % ARDAS_CONFIG['integration_period'])
    sys_logger.info('')
    sys_logger.info('Sensors:')
    for s in SENSORS:
        sys_logger.info('sensor ' + s.sensor_id + ':')
        sys_logger.info('   quantity: ' + s.quantity)
        sys_logger.info('   units: ' + s.units)
        sys_logger.info('   processing method: ' + repr(s.processing_method))
        sys_logger.info('   processing parameters: ' + repr(s.processing_parameters))
        sys_logger.info('   logging output to influxDB: ' + repr(s.log))
        sys_logger.info('')
    try:
        slave_io = serial.Serial(ARDAS_CONFIG['tty'], baudrate=57600, timeout=0.1, bytesize=serial.EIGHTBITS,
                                 parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                                 dsrdtr=False, rtscts=False, xonxoff=False)
        slave_io.reset_output_buffer()
        slave_io.reset_input_buffer()
        sys_logger.info('Saving data to ' + data_log_filename)
        sys_logger.info('Raw data: ' + str(raw_data))
    except IOError as e:
        sys_logger.error('*** Cannot open serial connexion with slave! : ' + str(e))
        status &= False
    try:
        sys_logger.debug('Master binding on (%s, %d)...' % (local_host, local_port))
        master_socket.bind((local_host, local_port))
        master_socket.listen(1)
        sys_logger.debug('Binding done!')
    except IOError as e:
        sys_logger.error('*** Cannot open server socket!' + str(e))  # TODO : What if raspardas cannot connect to server
        status &= False

    if influxdb_logging:
        try:
            sys_logger.info('Logging to database: %s' % DATABASE['dbname'])
            client = InfluxDBClient(DATABASE['host'], DATABASE['port'], DATABASE['user'], DATABASE['password'],
                                    DATABASE['dbname'])
        except:
            sys_logger.error('*** Unable to log to database %s' % DATABASE['dbname'])

    if raw_data:
        msg = 'Data is not calibrated'
        if influxdb_logging:
            msg += ' - It will not be logged in the database.'
        sys_logger.warning(msg)

    if status:
        try:
            station = ARDAS_CONFIG['station']
            net_id = ARDAS_CONFIG['net_id']
            integration_period = ARDAS_CONFIG['integration_period']

            pause = True
            # master_queue.put(cmd)
            slave_listener = Thread(target=listen_slave)
            slave_listener.setDaemon(True)
            slave_listener.start()
            slave_talker = Thread(target=talk_slave)
            slave_talker.setDaemon(True)
            slave_talker.start()

            sys_logger.info('Configuring ArDAS...')
            start_sequence()
            sys_logger.info('ArDAS configured !')

            master_connector = Thread(target=connect_master)
            master_connector.setDaemon(True)
            master_connector.start()
            master_talker = Thread(target=talk_master)
            master_talker.setDaemon(True)
            master_talker.start()
            master_listener = Thread(target=listen_master)
            master_listener.setDaemon(True)
            master_listener.start()
            pause = False

            sys_logger.info('*** Starting logging... ***')

            while not stop:
                sleep(0.25)

            sys_logger.info('Exiting - Waiting for threads to end...')
            slave_listener.join()
            master_talker.join()
            master_listener.join()
            master_connector.join()
            slave_talker.join()

        finally:
            sys_logger.info('Exiting - Closing file and communication ports...')
            try:
                slave_io
            except:
                pass
            else:
                slave_io.close()
            sys_logger.info('Exiting raspardas')
            sys_logger.info('****************************')
            sys_logger.info('***    SESSION ENDING    ***')
            sys_logger.info('****************************')
            sys_logger.info('')
    else:
        sys_logger.info('Exiting raspardas')
        try:
            slave_io.close()
        except:
            pass
