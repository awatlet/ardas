from threading import Thread, Event
from ardas.sensor_tools import generate_w1temp_sensors, TempSensor
import datetime
from time import sleep
import queue


def pause_until(next):
    """ Pauses until next

    :param next: datetime.datetime.timestamp
    """

    while True:
        now = datetime.datetime.utcnow().timestamp()
        diff = next - now
        if diff <= 0:
            break
        if diff <= 0.1:
            sleep(0.001)
        elif diff <= 0.5:
            sleep(0.01)
        elif diff <= 1.5:
            sleep(0.1)
        else:
            sleep(1)


class Sampler(Thread):
    def __init__(self, stop_event, interval, sensors, sampler_queue=None):
        Thread.__init__(self)
        self.stop_event = stop_event
        self.__measure_interval = interval
        self.sensors = sensors
        self.queue = sampler_queue

    @property
    def measure_interval(self):
        """ Gets measure_interval
        """
        return self.__measure_interval

    @measure_interval.setter
    def measure_interval(self, val):
        self.__measure_interval = val

    def run(self):
        while not self.stop_event.isSet():
            pass


class W1Sampler(Sampler, TempSensor):
    def run(self):
        sample_before = {}
        sample_after = {}
        sample = {}
        for i in self.sensors:
            sample_before[i.id] = (datetime.datetime.utcnow().timestamp(), i.get_temperature())
            sample_after[i.id] = sample_before[i.id]
            sample[i.id] = sample_before[i.id]
        next_sample_time = datetime.datetime.utcnow().timestamp()
        while not self.stop_event.isSet():
            for i in self.sensors:
                sample_after[i.id] = (datetime.datetime.utcnow().timestamp(), i.get_temperature())
                value = sample_before[i.id][1] + (next_sample_time - sample_before[i.id][0]) \
                        / (sample_after[i.id][0] - sample_before[i.id][0]) \
                        * (sample_after[i.id][1] - sample_before[i.id][1])
                sample[i.id] = (next_sample_time, value)
                sample_before[i.id] = sample_after[i.id]
                data = {'tags': {'sensor': '%s%s' % (i.slave_prefix, i.id)},
                        'time': datetime.datetime.fromtimestamp(sample[i.id][0]).strftime('%Y-%m-%d %H:%M:%S %Z'),
                        'fields': {'value': sample[i.id][1]}}
                self.queue.put(data)
            next_sample_time = next_sample_time + self.measure_interval
            pause_until(next_sample_time)


if __name__ == '__main__':
    sampler_queue = queue.Queue()
    try:
        s = TempSensor()
        sensors = s.get_available_sensors()
    except:
        sensors = generate_w1temp_sensors(7)
    stop = Event()
    s = W1Sampler(stop_event=stop, interval=5, sensors=sensors, sampler_queue=sampler_queue)
    s.start()
    k = 0
    kmax = 20
    while k < kmax:
        try:
            print(sampler_queue.get(timeout=1.0))
        except queue.Empty:
            pass
        k += 1
        sleep(1)
    stop.set()
    s.join(timeout=1.0)
    empty_queue = False
    while not empty_queue:
        try:
            print(sampler_queue.get(timeout=1.0))
        except queue.Empty:
            empty_queue = True

