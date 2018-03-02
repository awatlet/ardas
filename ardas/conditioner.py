from threading import Thread, Event
from time import sleep
from ardas.sampler import W1Sampler
from ardas.sensor_tools import TempSensor, generate_w1temp_sensors
from ardas.samples_conditioners import generate_w1temp_sensor_samples_conditioners
import queue


class Conditioner(Thread):
    def __init__(self, stop_event, samples_conditioners, sampler_queue, logger_queue):
        Thread.__init__(self)
        self.stop_event = stop_event
        self.__samples_conditioners = samples_conditioners
        self.sampler_queue = sampler_queue
        self.logger_queue = logger_queue

    @property
    def samples_conditioners(self):
        """ Gets and sets sensor id
        """
        return self.__samples_conditioners

    @samples_conditioners.setter
    def samples_conditioners(self, val):
        self.__samples_conditioners = val

    def run(self):
        while not self.stop_event.isSet():
            try:
                sample = self.sampler_queue.get(timeout=1.0)
                if sample is not None:
                    s_id = sample['tags']['sensor']
                    sc = self.samples_conditioners[s_id]
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
    samples_conditioners = generate_w1temp_sensor_samples_conditioners(sensors=sensors)
    conditioner = Conditioner(stop_event=stop, samples_conditioners=samples_conditioners, sampler_queue=sampler_queue,
                              logger_queue=logger_queue)
    sampler.start()
    conditioner.start()
    k = 0
    kmax = 20
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
