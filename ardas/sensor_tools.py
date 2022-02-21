import numpy as np
import os
from pathlib import Path
from pickle import dump, load
import logging
import RPi.GPIO as GPIO
import time

cur_dir = os.path.dirname(os.path.realpath(__file__))
GPIO.setmode(GPIO.BCM)


def polynomial(value, coefs):
    """Compute polynomial using Horner method

    :param value: given value of the variable
    :param coefs: coefficients of the polynomial
    :return: evaluation of polynomial for the given value of the variable
    :rtype: float
    """
    result = coefs[-1]
    for i in range(-2, -len(coefs) - 1, -1):
        result = result * value[-1] + coefs[i]
    result = result[0]
    assert isinstance(result, float)
    return result


def running_average(x, coefs):
    """Compute a running average (not centered)

    :param x: np.array of samples used to compute the running average
    :return: evaluation of the running average
    :rtype: float
    """

    return np.mean(x)


def activate_pin(pin, delay, safe_pins=(12, 6, 13, 16, 19, 20, 26, 21)):
    """ Activates a pin of the raspberry pi in output mode for the number of seconds sepcified in delay"""
    if pin in safe_pins:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(GPIO.HIGH)
        logging.info('Activating ' + pin + ' for ' + delay + ' seconds.')
        time.sleep(delay)
        GPIO.output(pin, GPIO.LOW)
        logging.info('Deactivating ' + pin + '.')
    else:
        logging.warning('Pin number ' + pin + ' is not in safe_pins. Skipped activation pin '+ pin + '.')


def running_median(x, coefs):
    """Compute a running average (not centered)

    :param x: np.array of samples used to compute the running median
    :return: evaluation of the running median
    :rtype: float
    """

    return np.median(x)


def open_valve_if_full(x, threshold=1600.,  pin=12, delay=30., safe_pins=(12)):
    logging.debug('Sensor freq. :' + x + 'Hz')
    if running_median(x, None) > threshold:
        activate_pin(pin, delay, safe_pins)


def load_sensor(sensor_id):
    """Loads a sensor object from a sensor '.ssr' file

    :param sensor_id: a unique identification number of the sensor
    :return: a sensor object
    :rtype: sensor"""
    f_name = cur_dir + '/sensor_' + sensor_id + '.ssr'
    with open(f_name, 'rb') as sensor_file:
        sensor = load(sensor_file)
    return sensor


class FMSensor(object):
    def __init__(self, sensor_id='0000', processing_method=polynomial, processing_parameters=(0., 1., 0., 0., 0.),
                 quantity='freq.', units='Hz', output_format='%11.4f', short_term_memory=1, log_output=True):
        self.sensor_id = sensor_id
        self.processing_method = processing_method
        self.processing_parameters = processing_parameters
        self._value = np.empty((short_term_memory,1))
        self.short_term_memory = short_term_memory
        self._value[:] = np.nan
        self.quantity = quantity
        self.units = units
        self.output_format = output_format
        self.log = log_output

    @property
    def sensor_id(self):
        """ Gets and sets sensor id
        """
        return self.__sensor_id

    @sensor_id.setter
    def sensor_id(self, val):
        self.__sensor_id = str(val[:4])

    @property
    def value(self):
        """ Gets and sets sensor value
        """
        return self._value

    @value.setter
    def value(self, val):
        assert isinstance(val, float)
        self._value = np.roll(self._value, -1)
        self._value[-1] = val


    @property
    def units(self):
        """ Gets and sets sensor value
        """
        return self.__units

    @units.setter
    def units(self, val):
        self.__units = val

    def output(self, value=None):
        """Outputs an output computed using the processing method and parameters

        :return: processed quantity
        :rtype: float
        """

        if value is None:
            value = self._value
        else:
            assert isinstance(np.array())
        output = self.processing_method(value, self.processing_parameters)
        return output

    def output_repr(self, value=None):
        """Gets a representation of the output

        :return: representation of the processed quantity
        :rtype: string
        """

        if value is None:
            value = self.value
        try:
            s = self.output_format + ' ' + self.units
            calibrated_output = s % self.output(value)
        except Exception as e:
            calibrated_output = '*** error : %s ***' % e
        assert isinstance(calibrated_output, str)
        return calibrated_output

    def save(self):
        """Save the sensor as a serialized object to a file """
        f_name = cur_dir + '/sensor_' + self.sensor_id + '.ssr'
        if Path(f_name).exists():
            logging.warning('Sensor file ' + f_name + ' already exists, unable to save sensor')
        else:
            with open(f_name, 'wb') as sensor_file:
                dump(self, sensor_file)


class UncalibratedFMSensor(FMSensor):
    """ A subclass of the sensor object with a simpler """
    def __init__(self, sensor_id='0000', log_output=True):
        super().__init__(sensor_id=sensor_id, log_output=log_output)


if __name__ == '__main__':
    #t = polynomial(25000, [-16.9224032438, 0.0041525221, -1.31475837290789e-07, 2.39122208189129e-12,
    #                       -1.72530800355418e-17])
    #print(t)
    #print(cur_dir)
    # sensor = FMSensor(sensor_id='9999', processing_method=running_average, processing_parameters=None,
    #                   short_term_memory=3, log_output=False)
    # while True:
    #     reply = input('Please enter sensor value')
    #     sensor.value = float(reply)
    #     print(sensor.output())
    sensor = FMSensor(sensor_id='9999', processing_method=polynomial,
                      processing_parameters=(-16.922, 0.0041525221, -1.314e-07, 2.391e-12, -1.725e-17),
                      log_output=False)
    sensor.value = 25000.
    print(sensor.output())

