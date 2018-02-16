from threading import Thread, Event
from ardas.sensor_tools import generate_w1temp_sensors, generate_w1temp_sensors_conditioners, TempSensor
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
    def __init__(self, stop_event, interval, sensors_conditioners, sampler_queue=None):
        Thread.__init__(self)
        self.stop_event = stop_event
        self.__measure_interval = interval
        self.sensors_conditioners = sensors_conditioners
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
        for j in self.sensors_conditioners:
            i = j.sensor
            sample_before[i.sensor_id] = (datetime.datetime.utcnow().timestamp(), self.get_temperature())
            sample_after[i.sensor_id] = sample_before[i.sensor_id]
            sample[i.sensor_id] = sample_before[i.sensor_id]
        next_sample_time = datetime.datetime.utcnow().timestamp()
        while not self.stop_event.isSet():
            for j in self.sensors_conditioners:
                i = j.sensor
                sample_after[i.sensor_id] = (datetime.datetime.utcnow().timestamp(), i.get_temperature())
                value = sample_before[i.sensor_id][1] + (next_sample_time - sample_before[i.sensor_id][0]) \
                        / (sample_after[i.sensor_id][0] - sample_before[i.sensor_id][0]) \
                        * (sample_after[i.sensor_id][1] - sample_before[i.sensor_id][1])
                sample[i.sensor_id] = (next_sample_time, value)
                sample_before[i.sensor_id] = sample_after[i.sensor_id]
                data = {'tags': {'sensor': '%s' % i.sensor_id, 'name': '%s' % j.name},
                        'time': datetime.datetime.fromtimestamp(sample[i.sensor_id][0]).strftime('%Y-%m-%d %H:%M:%S %Z'),
                        'fields': {'value': sample[i.sensor_id][1]}}
                self.queue.put(data)
            next_sample_time = next_sample_time + self.measure_interval
            pause_until(next_sample_time)


if __name__ == '__main__':
    w1temp_queue = queue.Queue()
    try:
        s = TempSensor()
        sensors = s.get_available_sensors()
    except:
        sensors = generate_w1temp_sensors(7)
    sensors_conditioners = generate_w1temp_sensors_conditioners(sensors=sensors)
    stop = Event()
    s = W1Sampler(stop_event=stop, interval=5, sensors_conditioners=sensors_conditioners, sampler_queue=w1temp_queue)
    s.start()
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
    s.join()
    empty_queue = False
    while not empty_queue:
        try:
            print(w1temp_queue.get(timeout=0.1))
        except queue.Empty:
            empty_queue = True