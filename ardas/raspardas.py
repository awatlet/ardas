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
# Message logging setup
log_path = path.join(path.dirname(__file__), 'logs')
if not path.isdir(log_path):
    mkdir(log_path)
log_file = path.join(log_path, LOGGING_CONFIG['file_name'])
msg_logger = logging.getLogger('msg_logger')

# Data logging setup
base_path = path.dirname(__file__)
data_path = path.join(base_path, 'data')
if not path.isdir(data_path):
    mkdir(data_path)
data_log_filename = path.join(data_path, DATA_LOGGING_CONFIG['file_name'])
data_logger = logging.getLogger('data_logger')

# Debug and logging
debug = LOGGING_CONFIG['debug_mode']
if debug:
    logging_level = logging.DEBUG
else:
    logging_level = logging.INFO

# Set message logging format and level
log_format = '%(asctime)-15s | %(process)d | %(levelname)s: %(message)s'
logging_to_console = LOGGING_CONFIG['logging_to_console']
msg_handler = CompressedSizedTimedRotatingFileHandler(log_file, max_bytes=LOGGING_CONFIG['max_bytes'],
                                                      backup_count=LOGGING_CONFIG['backup_count'],
                                                      when=LOGGING_CONFIG['when'],
                                                      interval=LOGGING_CONFIG['interval'])
msg_formatter = logging.Formatter(log_format)
msg_formatter.converter = gmtime
msg_formatter.datefmt = '%Y/%m/%d %H:%M:%S UTC'
msg_handler.setFormatter(msg_formatter)
msg_logger.addHandler(msg_handler)
msg_logger.setLevel(logging_level)

if logging_to_console:
    msg_logger.addHandler(logging.StreamHandler())

# Set data logging level and handler
data_logger.setLevel(logging.INFO)
data_handler = CompressedSizedTimedRotatingFileHandler(data_log_filename,
                                                       max_bytes=DATA_LOGGING_CONFIG['max_bytes'],
                                                       backup_count=DATA_LOGGING_CONFIG['backup_count'],
                                                       when=DATA_LOGGING_CONFIG['when'],
                                                       interval=DATA_LOGGING_CONFIG['interval'])
data_logger.addHandler(data_handler)

influxdb_logging = DATA_LOGGING_CONFIG['influxdb_logging']
client = None

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
    global msg_logger, data_logger, logging_level, data_log_filename, debug, client, slave_io
    """ This is the init sequence for the logging system """

    init_logging_status = True
    msg_logger.info('')
    msg_logger.info('****************************')
    msg_logger.info('*** NEW SESSION STARTING ***')
    msg_logger.info('****************************')
    msg_logger.info('Raspardas version ' + version + '.')
    msg_logger.info('')
    if debug:
        msg_logger.warning('Debug mode: ON')
    msg_logger.info('Logging level: %s' % logging_level)
    try:
        st = statvfs('.')
        available_space = st.f_bavail * st.f_frsize / 1024 / 1024
        msg_logger.info('Remaining disk space : %.1f MB' % available_space)
    except:
        pass
    msg_logger.info('Saving log to ' + log_file)
    msg_logger.info('ArDAS settings:')
    msg_logger.info('   station: %s' % ARDAS_CONFIG['station'])
    msg_logger.info('   net ID: %s' % ARDAS_CONFIG['net_id'])
    msg_logger.info('   integration period: %s' % ARDAS_CONFIG['integration_period'])
    msg_logger.info('')
    msg_logger.info('Sensors:')
    for s in SENSORS:
        msg_logger.info('sensor ' + s.sensor_id + ':')
        msg_logger.info('   quantity: ' + s.quantity)
        msg_logger.info('   units: ' + s.units)
        msg_logger.info('   processing method: ' + repr(s.processing_method))
        msg_logger.info('   processing parameters: ' + repr(s.processing_parameters))
        msg_logger.info('   logging output to influxDB: ' + repr(s.log))
        msg_logger.info('')
    try:
        slave_io = serial.Serial(ARDAS_CONFIG['tty'], baudrate=57600, timeout=0.1, bytesize=serial.EIGHTBITS,
                                 parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                                 dsrdtr=False, rtscts=False, xonxoff=False)
        sleep(1.0)
        slave_io.reset_output_buffer()
        slave_io.reset_input_buffer()
        msg_logger.info('Connected to serial port %s.' % ARDAS_CONFIG['tty'])
    except IOError as e:
        msg_logger.error('*** Cannot open serial connexion with slave! : ' + str(e))
        init_logging_status &= False
    try:
        msg_logger.info('Master binding on (%s, %d)...' % (local_host, local_port))
        master_socket.bind((local_host, local_port))
        master_socket.listen(1)
        msg_logger.info('Binding done!')
    except IOError as e:
        msg_logger.error('*** Cannot bind server socket binding on (%s, %d)!' + str(e))
        init_logging_status &= False  # TODO : What if raspardas cannot connect to server

    msg_logger.info('Saving data to ' + data_log_filename)
    msg_logger.info('Raw data: ' + str(raw_data))

    if influxdb_logging:
        try:
            msg_logger.info('Logging to database: %s' % DATABASE['dbname'])
            client = InfluxDBClient(DATABASE['host'], DATABASE['port'], DATABASE['user'], DATABASE['password'],
                                    DATABASE['dbname'])
        except:
            msg_logger.error('*** Unable to log to database %s' % DATABASE['dbname'])

    if raw_data:
        s = 'Data is not calibrated'
        if influxdb_logging:
            s += ' - It will not be logged in the database.'
        msg_logger.warning(s)
    return init_logging_status


def listen_slave():
    """This is a listener thread function.
    It processes items in the queue one after
    another.  This daemon threads runs into an
    infinite loop, and only exit when
    the main thread ends.
    """
    global stop, downloading, slave_io, data_queue, n_channels, slave_queue, master_queue, raw_data, \
        influxdb_logging, master_online, pause, msg_logger, data_logger

    sensors = SENSORS
    # slave_io.reset_input_buffer()
    # slave_io.reset_output_buffer()
    msg_logger.debug('Initiating listen_slave thread...')
    while not stop:
        # Read incoming data from slave (ArDAS)
        try:
            byte = b''
            msg = b''
            # msg_logger.debug('listen_slave: reading serial port')
            while byte != b'\r' and byte != b'$':
                byte = slave_io.read(1)
                msg += byte
                # msg_logger.debug(msg.decode('utf-8', 'replace'))
            # msg_logger.debug('listen_slave: message: %s' %msg.decode('ascii', errors='ignore'))
            if byte == b'$':
                record = byte
                record += slave_io.read(32)
                crc = slave_io.read(4)
                record_crc = int.from_bytes(crc, 'big')
                msg_crc = crc32(record)
                msg_logger.debug('record : %s' % str(record))
                msg_logger.debug('record_crc : %d' % record_crc)
                msg_logger.debug('msg_crc : %d' % msg_crc)
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
                        instr.append(int.from_bytes(record[9 + 2 * i:11 + 2 * i], 'big'))
                        freq.append(unpack_from('>f', record[17 + 4 * i:21 + 4 * i])[0])
                    decoded_record = '%04d ' % station + record_date.strftime('%Y %m %d %H %M %S') \
                                     + ' %04d' % integration_period
                    if raw_data:
                        decoded_record += ' R'
                    else:
                        decoded_record += ' C'
                        val = [0.] * n_channels
                    for i in range(n_channels):
                        val[i] = sensors[i].output(freq[i])
                        if raw_data:
                            decoded_record += ' %04d %11.4f' % (instr[i], freq[i])
                        else:
                            decoded_record += ' %04d %11.4f' % (instr[i], val[i])
                    decoded_record += '\n'
                    msg_logger.debug('Master connected: %s' % master_online)
                    if not raw_data:
                        cal_record = '%04d ' % station + record_date.strftime('%Y %m %d %H %M %S')
                        for i in range(n_channels):
                            sens_out = '| %04d: ' % instr[i]
                            sens_out += sensors[i].output_repr(freq[i])
                            sens_out += ' '
                            cal_record += sens_out
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
                        msg_logger.debug('Writing to InfluxDB : %s' % str(data))
                        client.write_points(data)
                else:
                    msg_logger.warning('*** Bad crc : corrupted data is not stored !')

            else:
                if len(msg) > 0:
                    try:
                        msg_logger.debug('Slave says : ' + msg.decode('ascii'))
                    except:
                        msg_logger.warning('*** listen_slave thread - Unable to decode slave message...')
                    if not downloading:
                        slave_queue.put(msg)
            sleep(0.2)
        except queue.Full:
            msg_logger.warning('*** Data or slave queue is full!')
        except serial.SerialTimeoutException:
            pass
    msg_logger.debug('Closing listen_slave thread...')


def talk_slave():
    """This is a talker thread function.
    It processes items in the queue one after
    another.  This daemon threads runs into an
    infinite loop, and only exit when
    the main thread ends.
    """
    global stop, slave_io, master_queue, msg_logger

    msg_logger.debug('Initiating talk_slave thread...')
    while not stop:
        try:
            msg = master_queue.get(timeout=0.25)
            try:
                msg_logger.debug('Saying to slave : ' + msg.decode('ascii')[:-1])
            except:
                msg_logger.warning('*** talk_slave thread - Unable to decode master message...')
            # msg_logger.debug('In waiting: ' + str(slave_io.in_waiting))
            # msg_logger.debug('Out waiting: ' + str(slave_io.out_waiting))
            msg_logger.debug('writing to slave...')
            slave_io.write(msg)
            # msg_logger.debug('In waiting after: ' + str(slave_io.in_waiting))
            # msg_logger.debug('Out waiting after: ' + str(slave_io.out_waiting))
            # slave_io.flush()  # NOTE: this line was commented as a test
        except queue.Empty:
            pass
        except serial.SerialTimeoutException:
            msg_logger.error('*** Could not talk to slave...')
        except Exception as err:
            msg_logger.warning('*** talk_slave thread - error: %s' % err)


    msg_logger.debug('Closing talk_slave thread...')


def connect_master():
    """This is a connection listener thread function.
    It waits for a connection from the master.
    This daemon threads runs into an
    infinite loop, and only exit when
    the main thread ends.
    """
    global stop, master_connection, master_socket, master_online, msg_logger

    msg_logger.debug('Initiating connect_master thread...')
    while not stop:
        try:
            if not master_online:
                msg_logger.info('Waiting for master...')
                master_connection, addr = master_socket.accept()
                msg_logger.info('Master connected, addr: ' + str(addr))
                master_online = True
        except:
            msg_logger.error('*** Master connection error!')

    if master_online:
        msg = b'\n*** Ending connection ***\n\n'
        master_connection.send(msg)
    master_connection.close()
    msg_logger.debug('Closing connect_master thread...')


def listen_master():
    """This is a listener thread function.
    It processes items in the queue one after
    another.  This daemon threads runs into an
    infinite loop, and only exit when
    the main thread ends.
    """
    global stop, master_connection, master_queue, master_online, raw_data, pause, msg_logger

    msg_logger.debug('Initiating listen_master thread...')
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
                        msg_logger.debug('Master says : ' + msg.decode('ascii'))
                    except:
                        msg_logger.warning('*** listen_master thread - Unable to decode master message...')
                    if msg[:-1] == b'#XB':
                        msg_logger.info('Full download is not available')
                    elif msg[:-1] == b'#XP':
                        msg_logger.info('Partial download request')
                    elif msg[:-1] == b'#XS':
                        msg_logger.info('Aborting download request')
                    elif msg[:-1] == b'#ZF':
                        msg_logger.info('Reset request')
                    elif msg[:-1] == b'#PA':
                        if pause:
                            msg_logger.info('Resume data logging')
                        else:
                            msg_logger.info('Pause data logging')
                        pause = not pause
                    elif msg[:-1] == b'#RC':
                        raw_data = not raw_data
                        if raw_data:
                            msg_logger.info('Switching to raw data.')
                        else:
                            msg_logger.info('Switching to calibrated data.')
                    elif msg[:-1] == b'#KL':
                        msg_logger.info('Stop request')
                        stop = True
                    else:
                        master_queue.put(msg)
            except queue.Full:
                msg_logger.error('*** Master queue is full!')
            except:
                msg_logger.warning('Master connection lost...')
                master_online = False
    msg_logger.debug('Closing listen_master thread...')


def talk_master():
    """This is a talker thread function.
    It processes items in the queue one after
    another.  This daemon threads runs into an
    infinite loop, and only exit when
    the main thread ends.
    """
    global stop, downloading, master_connection, slave_queue, master_online, msg_logger

    msg_logger.debug('Initiating talk_master thread...')
    while not stop:
        if master_online:
            try:
                if not downloading:
                    msg = slave_queue.get(timeout=0.25)
                    try:
                        msg_logger.debug('Saying to master :' + msg.decode('utf-8'))
                        master_connection.send(msg)
                    except:
                        msg_logger.warning('*** talk_master thread - Unable to decode slave message...')
                        master_connection.send(msg)

            except queue.Empty:
                pass
            except:
                msg_logger.warning('Master connection lost...')
                master_online = False
    msg_logger.debug('Closing talk_master thread...')


def start_sequence():
    global master_queue, slave_queue, n_channels, msg_logger

    msg_logger.debug('Initiating start sequence...')
    msg_logger.debug('____________________________')
    msg_logger.debug('start_sequence : Wake up slave...')
    if debug:
        reply = False
        while not reply:
            msg = b'-999\r\n'  # FIX: Should be \r
            master_queue.put(msg)
            msg_logger.debug('start_sequence : Calling all ArDAS')
            msg = b''
            k = 10
            sleep(0.75)
            while k > 0 and not reply:  # FIX: this does not seem to work properly each time (it loops endlessly)
                try:
                    msg = slave_queue.get(timeout=0.25)
                    if msg != b'':
                        if b'Hey!' in msg:
                            msg_logger.debug('start_sequence : Reply received!')
                            reply = True
                        else:
                            msg_logger.debug('start_sequence : No proper reply received yet...')
                    else:
                        msg_logger.debug('start_sequence : No message received yet...')
                except queue.Empty:
                    msg_logger.debug('start_sequence : Timed out...')
                    sleep(0.25)
                    k -= 1
    reply = False
    while not reply:
        msg = b'-' + bytes(ARDAS_CONFIG['net_id'].encode('ascii')) + b'\r\n'  # FIX: Should be /r
        master_queue.put(msg)
        msg_logger.debug('start_sequence : Sending wake-up command')
        msg = b''
        k = 10
        while k > 0 and not reply:
            try:
                msg = slave_queue.get(timeout=0.25)
            except queue.Empty:
                msg_logger.debug('start_sequence : Timed out...')
            if msg != b'':
                if len(msg) > 3 and msg[0:4] == b'!HI ':
                    msg_logger.debug('start_sequence : Reply received!')
                    reply = True
                else:
                    msg_logger.debug('start_sequence : No proper reply received yet...')
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
        msg_logger.debug('start_sequence : Sending reconfig command')
        try:
            msg = slave_queue.get(timeout=0.25)
        except:
            pass
        if msg[0:4] == b'!ZR ':
            msg_logger.debug('start_sequence : Reply received!')
            reply = True
        else:
            msg_logger.debug('start_sequence : No proper reply received yet...')

    reply = False
    while not reply:
        msg = b'#E0\r'
        master_queue.put(msg)
        msg_logger.debug('start_sequence : Sending no echo command')
        try:
            msg = slave_queue.get(timeout=0.25)
        except:
            pass
        if msg[0:4] == b'!E0 ':
            msg_logger.debug('start_sequence : Reply received!')
            reply = True
        else:
            msg_logger.debug('start_sequence : No proper reply received yet...')
    msg_logger.debug('start_sequence : Resetting clock...')
    c = ntplib.NTPClient()
    reply = False
    while not reply:
        try:
            msg_logger.debug('start_sequence : Getting time from NTP...')
            now = datetime.datetime.utcfromtimestamp(c.request('europe.pool.ntp.org').tx_time)
            msg = '#SD %04d %02d %02d %02d %02d %02d\r' % (
            now.year, now.month, now.day, now.hour, now.minute, now.second)
            master_queue.put(bytes(msg.encode('ascii')))
            msg_logger.debug('start_sequence : Setting ArDAS date from NTP server: %04d %02d %02d %02d %02d %02d' %
                             (now.year, now.month, now.day, now.hour, now.minute, now.second))
            try:
                msg = slave_queue.get(timeout=0.25)
            except:
                pass
            if msg[0:4] == b'!SD ':
                msg_logger.info('start_sequence : ArDAS date set from NTP server: %04d %02d %02d %02d %02d %02d' %
                                (now.year, now.month, now.day, now.hour, now.minute, now.second))
                reply = True
            else:
                msg_logger.debug('start_sequence : No proper reply received yet...')
        except:
            msg_logger.debug('start_sequence : Unable to get date and time from to NTP !')
    msg_logger.debug('Start sequence finished...')
    msg_logger.debug('__________________________')


if __name__ == '__main__':
    status = init_logging()

    if status:
        try:
            station = ARDAS_CONFIG['station']
            net_id = ARDAS_CONFIG['net_id']
            integration_period = ARDAS_CONFIG['integration_period']

            pause = True
            # master_queue.put(cmd)
            slave_talker = Thread(target=talk_slave)
            slave_talker.setDaemon(True)
            slave_talker.start()
            slave_listener = Thread(target=listen_slave)
            slave_listener.setDaemon(True)
            slave_listener.start()

            msg_logger.info('Configuring ArDAS...')
            start_sequence()
            msg_logger.info('ArDAS configured !')

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

            msg_logger.info('*** Starting logging... ***')

            while not stop:
                sleep(0.25)

            msg_logger.info('Exiting - Waiting for threads to end...')
            slave_listener.join()
            master_talker.join()
            master_listener.join()
            master_connector.join()
            slave_talker.join()

        finally:
            msg_logger.info('Exiting - Closing file and communication ports...')
            try:
                slave_io
            except:
                pass
            else:
                slave_io.close()
            msg_logger.info('Exiting raspardas')
            msg_logger.info('****************************')
            msg_logger.info('***    SESSION ENDING    ***')
            msg_logger.info('****************************')
            msg_logger.info('')
    else:
        msg_logger.info('Exiting raspardas')
        try:
            slave_io.close()
        except:
            pass
