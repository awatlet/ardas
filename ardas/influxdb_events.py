from ardas.compressed_sized_timed_rotating_logger import CompressedSizedTimedRotatingFileHandler
from influxdb import InfluxDBClient
from time import gmtime, sleep
import datetime
import logging
from os import path, mkdir
from ardas.settings import DATABASE, DATA_LOGGING_CONFIG, LOGGING_CONFIG


def influxdb_log_event(influxdb_client, title, default_tags, event_args,  msg_logger):
    """ Log an event in the influxdb series

    :param influxdb_client:
    :param title:
    :param default_tags:
    :param event_args:
    :param msg_logger:
    :param event_time:
    :return:
    """
    decoded_event_args = decode_event_args(event_args, default_tags)
    event = [{'measurement': 'events', 'time': decoded_event_args['event_time'],
             'fields': {'value': 1, 'tags': decoded_event_args['tags'], 'text': decoded_event_args['comment'],
                        'title': title}
              }]
    msg_logger.debug('Writing event "%s: %s" with tag(s) "%s" to %s @%s'
                     % (title, decoded_event_args['comment'], decoded_event_args['tags'], DATABASE['dbname'],
                        decoded_event_args['event_time']))
    event_written = False
    while not event_written:
        try:
            influxdb_client.write_points(event)
            event_written = True
        except Exception as e:
            msg_logger.error(e)
            msg_logger.debug('Unable to store event "%s: %s" with tag(s) "%s" to %s @%s'
                             % (title, decoded_event_args['comment'], decoded_event_args['tags'], DATABASE['dbname'],
                                decoded_event_args['event_time']))
            sleep(5)
            msg_logger.debug('Retry storing event "%s: %s" with tag(s) "%s" to %s @%s'
                             % (title, decoded_event_args['comment'], decoded_event_args['tags'], DATABASE['dbname'],
                                decoded_event_args['event_time']))
    msg_logger.info('Event "%s" with tag(s) "%s" written to %s @%s'
                    % (decoded_event_args['comment'], decoded_event_args['tags'], DATABASE['dbname'],
                       decoded_event_args['event_time']))


def influxdb_clean_events(influxdb_client, msg_logger):
    """ Erase all events in influxdb series

    :param influxdb_client:
    :param msg_logger:
    :return:
    """
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


def decode_event_args(event_args, default_tags='message'):
    """ Decodes event arguments of the type [comment text] [-tags tag1 tag2 ...] [-datetime YYYY mm dd HH MM SS]

    :param event_args: string that contain the event arguments
    :param default_tags: comma separated default tags to add to tags given in arguments
    :return: a dict of
    """
    s = event_args.strip()
    comment = ''
    if s.find('-') == 0:  # command args starting with an option (no comment)
        msg_split = 0
    else:
        msg_split = s.find(' -')
        if msg_split == -1:
            msg_split = len(s)
        comment = s[:msg_split].strip()
    if msg_split > 0:
        opts = [i.split(' ') for i in s[msg_split+2:].split(' -')]
    elif msg_split == 0:
        opts = [i.split(' ') for i in s[msg_split+1:].split(' -')]
    else:
        opts = None
    decoded_event_args = {}
    if opts is not None:
        for i in opts:
            if i[0] != '':
                option = i[0]
                values = i[1:]
                decoded_event_args.update({option: values})
    tags = decoded_event_args.get('tags', None)
    if type(tags) is not list:
        decoded_event_args['tags'] = default_tags
    else:
        tags = []
        for i in default_tags.split(','):
            tags.append(i.strip())
        for i in decoded_event_args['tags']:
            tags.append(i.strip())
        tags = ', '.join([i for i in tags])
        decoded_event_args['tags'] = tags
    event_time = decoded_event_args.get('datetime', None)
    if event_time is not None:
        decoded_event_args.pop('datetime')
        event_time = [int(i) for i in event_time]
        if len(event_time) < 6:
            for i in range(len(event_time),6):
                    event_time[i] = 0
        elif len(event_time) > 6:
            event_time = event_time[0:6]
        event_time = datetime.datetime(event_time[0], event_time[1], event_time[2], event_time[3], event_time[4], event_time[5])
    else:
        event_time = datetime.datetime.utcnow()
    decoded_event_args['event_time'] = event_time.isoformat()
    if comment == '':
        comment = 'No comment...'
    decoded_event_args['comment'] = comment
    return decoded_event_args


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
                tags = 'info, message'
                event_args = 'This is a test of datetime argument 4°C -tags test enhancement -datetime 2018 02 12 16 49 00'
                title = 'TITLE'
                influxdb_log_event(influxdb_client=influxdb_client, title=title, default_tags=tags,
                                   event_args=event_args, msg_logger=msg_logger)
