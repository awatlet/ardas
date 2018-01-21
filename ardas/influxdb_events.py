from ardas.compressed_sized_timed_rotating_logger import CompressedSizedTimedRotatingFileHandler
from influxdb import InfluxDBClient
from time import gmtime, sleep
import datetime
import logging
from os import path, mkdir
from ardas.settings import DATABASE, DATA_LOGGING_CONFIG, LOGGING_CONFIG


def influxdb_log_event(influxdb_client, tags, text, title,  msg_logger):
    event_time = datetime.datetime.utcnow().isoformat()
    event = [{'measurement': 'events', 'time': event_time,
             'fields': {'value': 1, 'tags': tags, 'text': text, 'title': title}
              }]
    msg_logger.debug('Writing event "%s" with tag(s) "%s" to %s @%s' % (text, tags, DATABASE['dbname'], event_time))
    event_written = False
    while not event_written:
        try:
            influxdb_client.write_points(event)
            event_written = True
        except Exception as e:
            msg_logger.error(e)
            msg_logger.debug('Unable to store event "%s" with tag(s) "%s" to %s @%s' % (text, tags, DATABASE['dbname'],
                                                                                        event_time))
            sleep(5)
            msg_logger.debug('Retry storing event "%s" with tag(s) "%s" to %s @%s' % (text, tags, DATABASE['dbname'],
                                                                                      event_time))
    msg_logger.info('Event "%s" with tag(s) "%s" written to %s @%s' % (text, tags, DATABASE['dbname'], event_time))


def influxdb_clean_events(influxdb_client, msg_logger):
    msg_logger.info('Deleting all events from %s' % DATABASE['dbname'])
    events_deleted = False
    while not events_deleted:
        try:
            influxdb_client.delete_series(measurement='events')
        except Exception as e:
            msg_logger.error(e)
            sleep(5)
            msg_logger.debug('Retry deleting events...')
    msg_logger.info('Events successfully deleted')


if __name__ == '__main__':
    stop = False
    influxdb_clean = False
    influxdb_logging = DATA_LOGGING_CONFIG['influxdb_logging']
    influxdb_client = None

    # setup loggers
    # Message logging setup
    log_path = path.join(path.dirname(__file__), 'logs')
    if not path.isdir(log_path):
        mkdir(log_path)
    log_file = path.join(log_path, LOGGING_CONFIG['file_name'])
    msg_logger = logging.getLogger('msg_logger')

    # Debug and logging
    debug = LOGGING_CONFIG['debug_mode']
    if debug:
        logging_level = logging.DEBUG
    else:
        logging_level = logging.INFO

    log_format = '%(asctime)-15s | %(process)d | %(levelname)s: %(message)s'
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

    if influxdb_logging:
        try:
            msg_logger.info('Connecting to database: %s' % DATABASE['dbname'])
            influxdb_client = InfluxDBClient(DATABASE['host'], DATABASE['port'], DATABASE['user'], DATABASE['password'],
                                             DATABASE['dbname'])
        except Exception as e:
            msg_logger.error('*** Unable to connect to database %s: %s' % (DATABASE['dbname'], e))
            stop = True

        if not stop:
            msg_logger.info('Connected to database: %s' % DATABASE['dbname'])

            if influxdb_clean:
                influxdb_clean_events(influxdb_client=influxdb_client, msg_logger=msg_logger)
            else:
                tags = 'Info, Message, Test'
                text = 'This is a test'
                title = 'TITLE'
                influxdb_log_event(influxdb_client=influxdb_client, text=text, tags=tags, title=title, msg_logger=msg_logger)
