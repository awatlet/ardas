from binascii import crc32
import datetime
import gzip  # TODO: Remove this when Compressed Sized Time Rotating Logging will be implemented
import logging
# from logging.handlers import RotatingFileHandler
import queue
import socket
from time import gmtime, sleep
from os import path, mkdir, statvfs
from struct import unpack_from
from threading import Thread, Lock
import ntplib
import serial
from ardas.settings import DATABASE, ARDAS_CONFIG, SENSORS, MASTER_CONFIG, LOGGING_CONFIG, DATA_LOGGING_CONFIG
from influxdb import InfluxDBClient
from ardas.compressed_sized_timed_rotating_logger import CompressedSizedTimedRotatingFileHandler

version = 'v1.1.2.40'
# Debug and logging
debug = LOGGING_CONFIG['debug_mode']
if debug:
    logging_level = logging.DEBUG
else:
    logging_level = logging.INFO
logging_to_console = LOGGING_CONFIG['logging_to_console']
influxdb_logging = DATA_LOGGING_CONFIG['influxdb_logging']

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
data_queue = queue.Queue()  # what should be written on disk

# Remaining initialization
data_file = ''
log_file = ''
status = True

# Data logging setup
# Set data and message logging paths
base_path = path.dirname(__file__)
data_path = path.join(base_path, 'raw')
if not path.isdir(data_path):
    mkdir(data_path)

data_log_filename = path.join(data_path, DATA_LOGGING_CONFIG['file_name'])
data_logger = logging.getLogger('MyLogger')
data_logger.setLevel(logging.INFO)
handler = CompressedSizedTimedRotatingFileHandler(data_log_filename,
                                                  maxBytes=DATA_LOGGING_CONFIG['max_bytes'],
                                                  backupCount=DATA_LOGGING_CONFIG['backup_count'],
                                                  when=DATA_LOGGING_CONFIG['when'],
                                                  interval=DATA_LOGGING_CONFIG['interval'])
data_logger.addHandler(handler)


def init_logging():
    global data_file, log_file, logging_level, logging_to_console
    """ This is the init sequence for the logging system """

    # Set data and message logging paths
    base_path = path.dirname(__file__)
    log_path = path.join(base_path, 'logs')
    raw_path = path.join(base_path, 'raw')
    if not path.isdir(log_path):
        mkdir(log_path)
    if not path.isdir(raw_path):
        mkdir(raw_path)
    data_file = path.join(raw_path, 'raw' + datetime.datetime.utcnow().strftime('_%Y%m%d_%H%M%S') + '.dat.gz')
    log_file = path.join(log_path, LOGGING_CONFIG['file_name'])

    # Set message logging format and level
    logging.Formatter.converter = gmtime
    log_format = '%(asctime)-15s | %(process)d | %(levelname)s: %(message)s'
    if logging_to_console:
        logging.basicConfig(format=log_format, datefmt='%Y/%m/%d %H:%M:%S UTC', level=logging_level,
                            handlers=[
                                CompressedSizedTimedRotatingFileHandler(log_file, maxBytes=LOGGING_CONFIG['max_bytes'],
                                                                        backupCount=LOGGING_CONFIG['backup_count'],
                                                                        when=LOGGING_CONFIG['when'],
                                                                        interval=LOGGING_CONFIG['interval']),
                                logging.StreamHandler()]
                            )
    else:
        logging.basicConfig(format=log_format, datefmt='%Y/%m/%d %H:%M:%S UTC', level=logging_level,
                            handlers=[
                                CompressedSizedTimedRotatingFileHandler(log_file, maxBytes=LOGGING_CONFIG['max_bytes'],
                                                                        backupCount=LOGGING_CONFIG['backup_count'],
                                                                        when=LOGGING_CONFIG['when'],
                                                                        interval=LOGGING_CONFIG['interval'])]
                            )
    logging.info('')
    logging.info('****************************')
    logging.info('*** NEW SESSION STARTING ***')
    logging.info('****************************')
    logging.info('Raspardas version ' + version + '.')
    logging.info('')
    if debug:
        logging.warning('Debug mode: ON')
    logging.info('Logging level: %s' % logging_level)
    try:
        st = statvfs('.')
        available_space = st.f_bavail * st.f_frsize / 1024 / 1024
        logging.info('Remaining disk space : %.1f MB' % available_space)
    except:
        pass
    logging.info('Saving log to ' + log_file)


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
                logging.warning('listen_slave: waiting new byte...')
                byte = slave_io.read(1)
                msg += byte
                logging.warning('listen_slave: %s', msg.decode('ascii', errors='replace'))
            if byte == b'$':
                record = byte
                record += slave_io.read(32)
                crc = slave_io.read(4)
                record_crc = int.from_bytes(crc, 'big')
                msg_crc = crc32(record)
                logging.debug('record : %s' % str(record))
                logging.debug('record_crc : %d' % record_crc)
                logging.debug('msg_crc : %d' % msg_crc)
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
                        if raw_data:
                            decoded_record += ' %04d %11.4f' % (instr[i], freq[i])
                        else:
                            val[i] = sensors[i].output(freq[i])
                            decoded_record += ' %04d %11.4f' % (instr[i], val[i])
                    decoded_record += '\n'
                    logging.debug('Master connected: %s' % master_online)
                    logging.warning('Raw data: ' + str(raw_data))  # TODO: remove
                    if not raw_data:
                        logging.warning('A')  # TODO: remove
                        cal_record = '%04d ' % station + record_date.strftime('%Y %m %d %H %M %S')
                        logging.warning('B')  # TODO: remove
                        for i in range(n_channels):
                            s = '| %04d: ' % instr[i]
                            logging.warning(s)  # TODO: remove
                            s += sensors[i].output_repr(freq[i])
                            s += ' '
                            logging.warning(s)  # TODO: remove
                            cal_record += s
                            logging.warning('D')  # TODO: remove
                        cal_record += '|'
                        logging.warning('E')  # TODO: remove
                        logging.warning(cal_record)  # TODO: remove
                        if not pause:
                            data_logger.info(cal_record.encode('utf-8'))
                        cal_record += '\n'
                        logging.warning('F')  # TODO: remove
                        if master_online:
                            slave_queue.put(cal_record.encode('utf-8'))
                    if influxdb_logging and not raw_data and not pause:
                        data = []
                        for i in range(n_channels):
                            if sensors[i].log:
                                data.append({'measurement': 'temperatures', 'tags': {'sensor': '%04d' % instr[i]},
                                             'time': record_date.strftime('%Y-%m-%d %H:%M:%S %Z'),
                                             'fields': {'value': val[i]}})
                        logging.debug('Writing to InfluxDB : %s' % str(data))
                        client.write_points(data)
                    # Send data to data_queue
                    logging.debug('Storing : ' + decoded_record)
                    data_queue.put(decoded_record.encode('utf-8'))
                else:
                    logging.warning('*** Bad crc : corrupted data is not stored !')

            else:
                if len(msg) > 0:
                    # Sort data to store on SD from data to repeat to master
                    try:
                        logging.info('Slave says : ' + msg.decode('ascii'))
                    except:
                        logging.warning('*** listen_slave thread - Unable to decode slave message...')
                    if not downloading:
                        slave_queue.put(msg)
            sleep(0.2)
        except queue.Full:
            logging.warning('*** Data or slave queue is full!')
        except serial.SerialTimeoutException:
            pass
    logging.debug('Closing listen_slave thread...')


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
                logging.debug('Saying to slave : ' + msg.decode('ascii'))
            except:
                logging.warning('*** talk_slave thread - Unable to decode master message...')
            slave_io.write(msg)
            logging.debug('In waiting: ' + str(slave_io.in_waiting))
            logging.debug('Out waiting: ' + str(slave_io.out_waiting))
            #slave_io.flush()  # NOTE: this line was commented as a test
        except queue.Empty:
            pass
        except serial.SerialTimeoutException:
            logging.error('*** Could not talk to slave...')

    logging.debug('Closing talk_slave thread...')


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
                logging.info('Waiting for master...')
                master_connection, addr = master_socket.accept()
                logging.info('Master connected, addr: ' + str(addr))
                master_online = True
        except:
            logging.error('*** Master connection error!')

    if master_online:
        msg = b'\n*** Ending connection ***\n\n'
        master_connection.send(msg)
    master_connection.close()
    logging.debug('Closing connect_master thread...')


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
                        logging.debug('Master says : ' + msg.decode('ascii'))
                    except:
                        logging.warning('*** listen_master thread - Unable to decode master message...')
                    if msg[:-1] == b'#XB':
                        logging.info('Full download is not available')
                    elif msg[:-1] == b'#XP':
                        logging.info('Partial download request')
                    elif msg[:-1] == b'#XS':
                        logging.info('Aborting download request')
                    elif msg[:-1] == b'#ZF':
                        logging.info('Reset request')
                    elif msg[:-1] == b'#CF':
                        logging.info('Change file request')
                        save_file()
                    elif msg[:-1] == b'#PA':
                        if pause:
                            logging.info('Resume data logging')
                        else:
                            logging.info('Pause data logging')
                        pause = not pause
                    elif msg[:-1] == b'#RC':
                        raw_data = not raw_data
                        if raw_data:
                            logging.info('Switching to raw data.')
                        else:
                            logging.info('Switching to calibrated data.')
                    elif msg[:-1] == b'#KL':
                        logging.info('Stop request')
                        stop = True
                    else:
                        master_queue.put(msg)
            except queue.Full:
                logging.error('*** Master queue is full!')
            except:
                logging.warning('Master connection lost...')
                master_online = False
    logging.debug('Closing listen_master thread...')


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
                        logging.debug('Saying to master :' + msg.decode('utf-8'))
                        master_connection.send(msg)
                    except:
                        logging.warning('*** talk_master thread - Unable to decode slave message...')
                        master_connection.send(msg)

            except queue.Empty:
                pass
            except:
                logging.warning('Master connection lost...')
                master_online = False
    logging.debug('Closing talk_master thread...')


def write_disk():
    """This is a writer thread function.
    It processes items in the queue one after
    another.  This daemon threads runs into an
    infinite loop, and only exit when
    the main thread ends.
    """
    global stop, sd_file_io, data_queue, sd_file_lock, pause

    offset = sd_file_io.tell()
    while not stop:
        try:
            msg = data_queue.get(timeout=0.1)
            logging.debug('Data queue length : %d' % data_queue.qsize())
            if len(msg) > 0:
                if not pause:
                    logging.debug('Writing to disk :' + msg.decode('ascii'))
                    sd_file_lock.acquire()
                    sd_file_io.seek(offset)
                    sd_file_io.write(msg)
                    sd_file_io.flush()
                    offset = sd_file_io.tell()
                    sd_file_lock.release()
        except queue.Empty:
            pass
    sd_file_io.flush()
    logging.debug('Closing write_disk thread...')


def save_file():
    """This is a save_file function.
    """
    global data_file, sd_file_io, sd_file_lock, master_connection

    sd_file_lock.acquire()
    sd_file_io.close()
    logging.info('File ' + data_file + ' saved.')

    base_path = path.dirname(__file__)
    data_file = path.join(base_path, 'raw' + datetime.datetime.utcnow().strftime('_%Y%m%d_%H%M%S') + '.dat.gz')
    sd_file_io = gzip.open(data_file, "ab+")
    sd_file_lock.release()
    logging.info('New file ' + data_file + ' created.')


def start_sequence():
    global master_queue, slave_queue, n_channels

    logging.debug('Initiating start sequence...')
    logging.debug('____________________________')

    while not slave_queue.empty():
        sleep(0.01)
    logging.debug('start_sequence : Wake up slave...')
    if debug:
        reply = False
        while not reply:
            msg = b'-999\r\n'  # FIX: Should be /r
            master_queue.put(msg)
            logging.debug('start_sequence : Calling all ArDAS')
            msg = b''
            k = 10
            while k > 0 and not reply:  # FIX: this does not seem to work properly each time (it loops endlessly)
                try:
                    msg = slave_queue.get(timeout=0.25)
                except queue.Empty:
                    logging.debug('start_sequence : Timed out...')
                if msg != b'':
                    try:
                        logging.debug('start_sequence : Incoming message: ' + msg.decode('ascii'))
                    except UnicodeDecodeError as e:
                        logging.debug('start_sequence : slave_queue exception...' + str(e))
                    if b'Hey!' in msg:
                        logging.debug('start_sequence : Reply received!')
                        reply = True
                    else:
                        logging.debug('start_sequence : No proper reply received yet...')
                else:
                    logging.debug('start_sequence : No message received yet...')
                # sleep(0.25)
                k -= 1
    reply = False
    while not reply:
        msg = b'-' + bytes(ARDAS_CONFIG['net_id'].encode('ascii')) + b'\r\n'  # FIX: Should be /r
        master_queue.put(msg)
        logging.debug('start_sequence : Sending wake-up command')
        msg = b''
        k = 10
        while k > 0 and not reply:
            try:
                msg = slave_queue.get(timeout=0.25)
            except queue.Empty:
                logging.debug('start_sequence : Timed out...')
            if msg != b'':
                try:
                    logging.debug('start_sequence : Incoming message: ' + msg.decode('ascii'))  # TODO: remove this
                except UnicodeDecodeError as e:
                    logging.debug('start_sequence : slave_queue exception...' + str(e))
                if len(msg) > 3 and msg[0:4] == b'!HI ':
                    logging.debug('start_sequence : Reply received!')
                    reply = True
                else:
                    logging.debug('start_sequence : No proper reply received yet...')
            # sleep(0.25)
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
        logging.debug('start_sequence : Sending reconfig command')
        try:
            msg = slave_queue.get(timeout=0.25)
        except:
            pass
        if msg[0:4] == b'!ZR ':
            logging.debug('start_sequence : Reply received!')
            reply = True
        else:
            logging.debug('start_sequence : No proper reply received yet...')
    reply = False
    while not reply:
        msg = b'#E0\r'
        master_queue.put(msg)
        logging.debug('start_sequence : Sending no echo command')
        try:
            msg = slave_queue.get(timeout=0.25)
        except:
            pass
        if msg[0:4] == b'!E0 ':
            logging.debug('start_sequence : Reply received!')
            reply = True
        else:
            logging.debug('start_sequence : No proper reply received yet...')
    logging.debug('start_sequence : Resetting clock...')
    c = ntplib.NTPClient()
    reply = False
    while not reply:
        try:
            logging.debug('start_sequence : Getting time from NTP...')
            now = datetime.datetime.utcfromtimestamp(c.request('europe.pool.ntp.org').tx_time)
            msg = '#SD %04d %02d %02d %02d %02d %02d\r' % (now.year, now.month, now.day, now.hour, now.minute, now.second)
            master_queue.put(bytes(msg.encode('ascii')))
            logging.debug('start_sequence : Setting ArDAS date from NTP server: %04d %02d %02d %02d %02d %02d' %
                         (now.year, now.month, now.day, now.hour, now.minute, now.second))
            try:
                msg = slave_queue.get(timeout=0.25)
            except:
                pass
            if msg[0:4] == b'!SD ':
                logging.info('start_sequence : ArDAS date set from NTP server: %04d %02d %02d %02d %02d %02d' %
                             (now.year, now.month, now.day, now.hour, now.minute, now.second))
                reply = True
            else:
                logging.debug('start_sequence : No proper reply received yet...')
        except:
            logging.debug('start_sequence : Unable to get date and time from to NTP !')
    logging.debug('Start sequence finished...')
    logging.debug('__________________________')

if __name__ == '__main__':
    init_logging()

    logging.info('ArDAS settings:')
    logging.info('   station: %s' % ARDAS_CONFIG['station'])
    logging.info('   net ID: %s' % ARDAS_CONFIG['net_id'])
    logging.info('   integration period: %s' % ARDAS_CONFIG['integration_period'])
    logging.info('   n_channels: %d' %len(SENSORS))
    logging.info('')
    logging.info('Sensors:')
    for s in SENSORS:
        logging.info('sensor ' + s.sensor_id + ':')
        logging.info('   quantity: ' + s.quantity)
        logging.info('   units: ' + s.units)
        logging.info('   processing method: ' + repr(s.processing_method))
        logging.info('   processing parameters: ' + repr(s.processing_parameters))
        logging.info('   logging output to influxDB: ' + repr(s.log))
        logging.info('')
    try:
        slave_io = serial.Serial(ARDAS_CONFIG['tty'], baudrate=57600, timeout=0.1, bytesize=serial.EIGHTBITS,
                                 parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                                 dsrdtr=False, rtscts=False, xonxoff=False)
        slave_io.reset_output_buffer()
        slave_io.reset_input_buffer()
        logging.info('Saving data to ' + data_file)
    except IOError as e:
        logging.error('*** Cannot open serial connexion with slave! : ' + str(e))
        status &= False
    try:
        logging.debug('Master binding on (%s, %d)...' % (local_host, local_port))
        master_socket.bind((local_host, local_port))
        master_socket.listen(1)
        logging.debug('Binding done!')
    except IOError as e:
        logging.error('*** Cannot open server socket!' + str(e))  # TODO : What if raspardas cannot connect to server
        status &= False
    try:
        sd_file_io = gzip.open(data_file, 'ab+')
        # sd_file_io = io.BufferedRandom(sd_file, buffer_size=128)
    except IOError as e:
        logging.error('*** Cannot open file ! : ' + str(e))
        status &= False

    if influxdb_logging:
        try:
            logging.info('Logging to database: %s' % DATABASE['dbname'])
            client = InfluxDBClient(DATABASE['host'], DATABASE['port'], DATABASE['user'], DATABASE['password'],
                                    DATABASE['dbname'])
        except:
            logging.error('*** Unable to log to database %s' % DATABASE['dbname'])

    if raw_data:
        msg = 'Data is not calibrated'
        if influxdb_logging:
            msg += ' - It will not be logged in the database.'
        logging.warning(msg)

    if status:
        try:
            station = ARDAS_CONFIG['station']
            net_id = ARDAS_CONFIG['net_id']
            integration_period = ARDAS_CONFIG['integration_period']

            pause = True
            # master_queue.put(cmd)
            sd_file_lock = Lock()
            disk_writer = Thread(target=write_disk)
            disk_writer.setDaemon(True)
            disk_writer.start()
            slave_listener = Thread(target=listen_slave)
            slave_listener.setDaemon(True)
            slave_listener.start()
            slave_talker = Thread(target=talk_slave)
            slave_talker.setDaemon(True)
            slave_talker.start()

            logging.info('Configuring ArDAS...')
            start_sequence()
            logging.info('ArDAS configured !')

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

            logging.info('*** Starting logging... ***')

            while not stop:
                sleep(0.2)

            logging.info('Exiting - Waiting for threads to end...')
            slave_listener.join()
            master_talker.join()
            master_listener.join()
            master_connector.join()
            slave_talker.join()
            disk_writer.join()

        finally:
            logging.info('Exiting - Closing file and communication ports...')
            try:
                slave_io
            except:
                pass
            else:
                slave_io.close()
            try:
                sd_file_io
            except:
                pass
            else:
                sd_file_io.close()
            logging.info('Exiting raspardas')
            logging.info('****************************')
            logging.info('***    SESSION ENDING    ***')
            logging.info('****************************')
            logging.info('')
    else:
        logging.info('Exiting raspardas')
        try:
            slave_io.close()
        except:
            pass
        try:
            sd_file_io.close()
        except:
            pass
