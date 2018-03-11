import numpy as np
from pathlib import Path
from pickle import dump
import logging
from ardas.samples_conditioners import SamplesConditioner, generate_w1temp_sensor_samples_conditioners

cur_dir = Path(__file__).resolve().parent


def no_logging(self, record, params=None):
    """Dummy logger: it does not log at all !

    :param self: calling object
    :param record : record to log
    :param params: None
    :return: status
    """

    status = True
    return status


class RecordsLogger(object):
    """ A class to handle sensors
    """
    def __init__(self, logger_id=None, logger_name='', logging_method=None, logging_parameters=None, log_output=True):
        self.__logger_name = logger_name
        self.logging_method = logging_method
        self.logging_parameters = logging_parameters
        self.__log = log_output  # TODO: keep this here?

    @property
    def logger_id(self):
        """Gets and sets logger id
        """
        return self.__logger_id

    @logger_id.setter
    def logger_id(self, val):
        self.__logger_id = str(val)

    @property
    def logger_name(self):
        """Gets and sets logger name
        """
        return self.__logger_name

    @logger_name.setter
    def logger_name(self, val):
        self.__logger_name = str(val)


class W1TempSensorRecordsLogger(SamplesConditioner):
    def __init__(self, logger_id, channel_name, logging_method=no_logging, logging_parameters=None):
        RecordsLogger.__init__(self, logger_id, channel_name=channel_name, logging_method=logging_method,
                               logging_parameters=logging_parameters, log_output=True)
        self.quantity = 'temp.'
        self.units = '°C'
        self.output_format = '%6.3f'


def generate_w1temp_sensor_records_loggers(nb_conditioners=2, samples_conditioners=None):
    if samples_conditioners is None:
        samples_conditioners = generate_w1temp_sensor_samples_conditioners(nb_conditioners)
    else:
        nb_conditioners = len(samples_conditioners)
    records_loggers = {}
    for i in range(nb_conditioners):
        s = W1TempSensorRecordsLogger(logger_id=str(i), logger_name='T%03d' % i)
        records_loggers.update({'%s%s' % (sensors[i].slave_prefix, sensors[i].id): s})
    return records_loggers


if __name__ == '__main__':
    pass
