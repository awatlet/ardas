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
                sample = self.sampler_queue.get()
                sc_id = sample['tags']['sensor']
                sc = self.sensors_conditioners[sc_id]
                sc.p
                data = {'tags': {'sensor': '%s%s' % (i.slave_prefix, i.id)},
                        'time': datetime.datetime.fromtimestamp(sample[i.id][0]).strftime('%Y-%m-%d %H:%M:%S %Z'),
                        'fields': {'value': sample[i.id][1]}}
                self.logger_queue.put(data)
            except queue.Empty:
                pass
            # for i in self.sensors:
            #     # i = j.sensor
            #     sample_before[i.id] = (datetime.datetime.utcnow().timestamp(), i.get_temperature())
            #     sample_after[i.id] = sample_before[i.id]
            #     sample[i.id] = sample_before[i.id]
            # next_sample_time = datetime.datetime.utcnow().timestamp()
            # while not self.stop_event.isSet():
            #     for i in self.sensors:
            #         # i = j.sensor
            #         sample_after[i.id] = (datetime.datetime.utcnow().timestamp(), i.get_temperature())
            #         value = sample_before[i.id][1] + (next_sample_time - sample_before[i.id][0]) \
            #                 / (sample_after[i.id][0] - sample_before[i.id][0]) \
            #                 * (sample_after[i.id][1] - sample_before[i.id][1])
            #         sample[i.id] = (next_sample_time, value)
            #         sample_before[i.id] = sample_after[i.id]
            #         data = {'tags': {'sensor': '%s%s' % (i.slave_prefix, i.id)},
            #                 'time': datetime.datetime.fromtimestamp(sample[i.id][0]).strftime('%Y-%m-%d %H:%M:%S %Z'),
            #                 'fields': {'value': sample[i.id][1]}}
            #         self.queue.put(data)
            #     next_sample_time = next_sample_time + self.measure_interval
            #     pause_until(next_sample_time)

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
    print(sensors_conditioners)
    conditioner = Conditioner(stop_event=stop, sensors_conditioners=sensors_conditioners, sampler_queue=sampler_queue,
                              logger_queue=logger_queue)
    sampler.start()
    conditioner.start()
    k = 0
    kmax = 10
    while k < kmax:
        try:
            print('.')  # sampler_queue.get(timeout=0.1))
        except queue.Empty:
            pass
        k +=1
        sleep(1)
    stop.set()
    sampler.join(timeout=1.0)
    conditioner.join(timeout=1.0)
    empty_queue = False
    while not empty_queue:
        try:
            print(logger_queue.get(timeout=0.1))
        except queue.Empty:
            empty_queue = True