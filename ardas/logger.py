from threading import Thread, Event
from time import sleep
from ardas.sampler import W1Sampler
from ardas.sensor_tools import TempSensor, generate_w1temp_sensors
from ardas.samples_conditioners import generate_w1temp_sensor_samples_conditioners
from ardas.conditioner import Conditioner
import queue


class Logger(Thread):
    def __init__(self, stop_event, channels_loggers, logger_queue, loggers=None):
        Thread.__init__(self)
        self.stop_event = stop_event
        self.__channels_loggers = channels_loggers
        self.logger_queue = logger_queue
        self.loggers = loggers

    @property
    def channels_loggers(self):
        """ Gets and sets channels loggers
        """
        return self.__channels_loggers

    @channels_loggers.setter
    def channels_loggers(self, val):
        self.__channels_loggers = val

    def run(self):
        while not self.stop_event.isSet():
            try:
                record = self.logger_queue.get(timeout=1.0)
                if record is not None:
                    print(record)
                    ch_id = record['tags']['channel']
                    cl = self.channels_loggers[ch_id]
                    cl.log()
            except queue.Empty:
                pass


if __name__ == '__main__':
    sampler_queue = queue.Queue()
    logger_queue = queue.Queue()
    try:
        s = TempSensor()
        sensors = s.get_available_sensors()
    except:
        sensors = generate_w1temp_sensors(7)
    stop = Event()
    sampler = W1Sampler(stop_event=stop, interval=5, sensors=sensors, sampler_queue=sampler_queue)
    sensors_conditioners = generate_w1temp_sensor_samples_conditioners(sensors=sensors)
    channels_loggers = None
    conditioner = Conditioner(stop_event=stop, samples_conditioners=sensors_conditioners, sampler_queue=sampler_queue,
                              logger_queue=logger_queue)
    logger = Logger(stop_event=stop, channels_loggers=channels_loggers, logger_queue=logger_queue)
    sampler.start()
    conditioner.start()
    logger.start()
    k = 0
    kmax = 10
    while k < kmax:
        k += 1
        sleep(1.0)
    stop.set()
    sampler.join(timeout=1.0)
    conditioner.join(timeout=1.0)
    empty_queue = False
    while not empty_queue:
        try:
            print(logger_queue.get(timeout=0.1))
        except queue.Empty:
            empty_queue = True
