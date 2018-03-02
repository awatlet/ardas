from threading import Thread, Event
from time import sleep
from ardas.sampler import W1Sampler
from ardas.sensor_tools import TempSensor, generate_w1temp_sensors, generate_w1temp_sensors_conditioners
import queue


class Conditioner(Thread):
    def __init__(self, stop_event, sensors_conditioners, sampler_queue, logger_queue, loggers=None):
        Thread.__init__(self)
        self.stop_event = stop_event
        self.__sensors_conditioners = sensors_conditioners
        self.sampler_queue = sampler_queue
        self.logger_queue = logger_queue
        self.loggers = loggers

    @property
    def sensors_conditioners(self):
        """ Gets and sets sensor id
        """
        return self.__sensors_conditioners

    @sensors_conditioners.setter
    def sensors_conditioners(self, val):
        self.__sensors_conditioners = val

    def run(self):
        while not self.stop_event.isSet():
            try:
                sample = self.sampler_queue.get(timeout=1.0)
                if sample is not None:
                    s_id = sample['tags']['sensor']
                    sc = self.sensors_conditioners[s_id]
                    data = sc.output(sample)
                    data['tags']['channel'] = '%s' % sc.channel_name
                    self.logger_queue.put(data)
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
    sensors_conditioners = generate_w1temp_sensors_conditioners(sensors=sensors)
    conditioner = Conditioner(stop_event=stop, sensors_conditioners=sensors_conditioners, sampler_queue=sampler_queue,
                              logger_queue=logger_queue)
    sampler.start()
    conditioner.start()
    k = 0
    kmax = 30
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
