from threading import Thread, Event
from time import sleep
from ardas.sampler import generate_w1temp_sensors, W1Sampler
from ardas import sensor_tools as st
import queue


class SensorConditioner(Thread):
    def __init__(self, stop_event, sensors, sampler_queue, logger_queue, loggers=None):
        Thread.__init__(self)
        self.__sensors = sensors
        self.sampler_queue = sampler_queue
        self.logger_queue = logger_queue
        self.loggers = loggers

    @property
    def sensors(self):
        """ Gets and sets sensor id
        """
        return self.__sensors

    @sensors.setter
    def sensors(self, val):
        self.__sensors = val

    def run(self):
        while not self.stop_event.isSet():
            pass

    def output_repr(self, id, value):
        """ Gets a representation of the output

        :param id: sensor identification
        :param value: value to condition
        :return: representation of the processed quantity
        :rtype: string
        """

        try:
            sensor = self.sensors[id]
            s = sensor.output_format + ' ' + sensor.units
            conditioned_output = s % sensor.output(value)
        except Exception as e:
            conditioned_output = '*** error : %s ***' % e
        assert isinstance(conditioned_output, str)
        return conditioned_output


if __name__ == '__main__':
    w1temp_queue = queue.Queue()
    logger_queue = queue.Queue()
    stop = Event()
    sensors = generate_w1temp_sensors(7)
    sampler = W1Sampler(stop_event=stop, interval=5, sensors=sensors, sampler_queue=w1temp_queue)
    c = SensorConditioner(stop_event=stop, sensors=sensors, sampler_queue=w1temp_queue, logger_queue=logger_queue)
    sampler.start()
    k = 0
    kmax = 20
    while k < 20:
        try:
            print(w1temp_queue.get(timeout=0.1))
        except queue.Empty:
            pass
        k +=1
        sleep(1)
    stop.set()
    sampler.join()
    empty_queue = False
    while not empty_queue:
        try:
            print(w1temp_queue.get(timeout=0.1))
        except queue.Empty:
            empty_queue = True