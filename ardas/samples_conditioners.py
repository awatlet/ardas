import numpy as np
from pathlib import Path
from pickle import dump
import logging
from ardas.sensor_tools import generate_w1temp_sensors

cur_dir = Path(__file__).resolve().parent


def polynomial(value, coefs):
    """Compute polynomial using Horner method

    :param value: given value of the variable
    :param coefs: coefficients of the polynomial
    :return: evaluation of polynomial for the given value of the variable
    :rtype: float
    """

    result = coefs[-1]
    for i in range(-2, -len(coefs) - 1, -1):
        result = result * value + coefs[i]
    assert isinstance(result, float)
    return result


def running_average(n):  # TODO: add self ?, refactor to deal with samples and not single values
    """Compute a running average (not centered)

    :param n: number of former samples used to compute the running average
    :return: evaluation of polynomial for the given value of the variable (freq)
    :rtype: float
    """

    samples_list = []
    average = None
    while True:
        new_sample = yield average
        if len(samples_list) == n:
            del samples_list[0]
        samples_list.append(new_sample)
        if len(samples_list) > 0:
            average = sum(samples_list) / len(samples_list)
        else:
            average = np.nan


def no_processing(self, sample, params=None):
    """Simple copy of the value

    :param self: calling object
    :param sample: value from sensor
    :param params: None
    :return: same value
    """

    assert (type(sample) is dict), 'sample should be a dict'
    sample['fields']['format'] = self.output_format
    sample['fields']['units'] = self.units
    sample['fields']['quantity'] = self.quantity
    sample['tags']['processing'] = 'no processing'
    return sample


class SamplesConditioner(object):
    """ A class to handle sensors
    """
    def __init__(self, sensor=None, channel_name='', processing_method=no_processing, processing_parameters=None,
                 quantity='', units='', output_format='%11.4f', log_output=True):
        self.sensor = sensor
        self.__channel_name = channel_name
        self.processing_method = processing_method
        self.processing_parameters = processing_parameters
        self.__quantity = quantity
        self.__units = units
        self.__output_format = output_format
        self.__log = log_output  # TODO: keep this here?

    @property
    def channel_name(self):
        """Gets and sets sensor name
        """
        return self.__channel_name

    @channel_name.setter
    def channel_name(self, val):
        self.__channel_name = str(val)

    @property
    def quantity(self):
        """Gets and sets sensor units
        """
        return self.__quantity

    @quantity.setter
    def quantity(self, val):
        self.__quantity = str(val)

    @property
    def units(self):
        """Gets and sets sensor units
        """
        return self.__units

    @units.setter
    def units(self, val):
        self.__units = val

    @property
    def output_format(self):
        """Gets and sets sensor units
        """
        return self.__output_format

    @output_format.setter
    def output_format(self, val):
        self.__output_format = val

    def output(self, sample):
        """Outputs an record computed using the processing method and parameters

        input sample should be in the form of a sample dict

        :return: record
        :rtype: dict
        """

        output = self.processing_method(self, sample, self.processing_parameters)
        return output

    def output_repr(self, sample):
        """Gets a representation of the output

        :return: representation of the processed quantity
        :rtype: string
        """

        try:
            s = self.output_format + ' ' + self.units
            calibrated_output = s % self.output(sample)
        except Exception as e:
            calibrated_output = '*** error : %s ***' % e
        assert isinstance(calibrated_output, str)
        return calibrated_output

    def save(self):  # TODO deal with sensors, samples conditioner (and channel loggers ?)
        """Save the sensor as a serialized object to a file """
        f_name = cur_dir / 'sensor_' + self.name + '.ssr'
        if Path(f_name).exists():
            logging.warning('Sensor file ' + f_name + ' already exists, unable to save sensor')
        else:
            with open(f_name, 'wb') as sensor_file:
                dump(self, sensor_file)


class FMSensorSamplesConditioner(SamplesConditioner):
    """A subclass of the SamplesConditioner object with a simpler interface"""
    def __init__(self, channel_name='0000', processing_method=polynomial, processing_parameters=(0., 1., 0., 0., 0.),
                 quantity='freq.', units='Hz'):
        SamplesConditioner.__init__(self, channel_name=channel_name, processing_method=processing_method,
                                    processing_parameters=processing_parameters, quantity=quantity, units=units)


class UncalibratedFMSensorSamplesConditioner(FMSensorSamplesConditioner):
    """A subclass of the FMSensorSamplesConditioner object with a simpler interface for raw output"""
    def __init__(self, channel_name='0000', log_output=True):
        FMSensorSamplesConditioner.__init__(channel_name=channel_name, log_output=log_output)


class W1TempSensorSamplesConditioner(SamplesConditioner):
    def __init__(self, sensor, channel_name, processing_method=no_processing, processing_parameters=None):
        SamplesConditioner.__init__(self, sensor=sensor, channel_name=channel_name, processing_method=processing_method,
                                    processing_parameters=processing_parameters, log_output=True)
        self.quantity = 'temp.'
        self.units = '°C'
        self.output_format = '%6.3f'


def generate_w1temp_sensor_samples_conditioners(nb_sensor=2, sensors=None):
    if sensors is None:
        sensors = generate_w1temp_sensors(nb_sensor)
    else:
        nb_sensor = len(sensors)
    sensors_conditioners = {}
    for i in range(nb_sensor):
        s = W1TempSensorSamplesConditioner(sensor=sensors[i], channel_name='T%03d' % i)
        sensors_conditioners.update({'%s%s' % (sensors[i].slave_prefix, sensors[i].id): s})
    return sensors_conditioners


if __name__ == '__main__':
    t = polynomial(25000, [-16.9224032438, 0.0041525221, -1.31475837290789e-07, 2.39122208189129e-12,
                           -1.72530800355418e-17])
    print(t)
    print(cur_dir)
