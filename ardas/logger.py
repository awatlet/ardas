from threading import Thread, Event
from time import sleep
from ardas.sampler import W1Sampler
from ardas.sensor_tools import TempSensor, generate_w1temp_sensors
from ardas.samples_conditioners import generate_w1temp_sensor_samples_conditioners
from ardas.records_loggers import generate_w1temp_sensor_records_loggers
from ardas.conditioner import Conditioner
import queue


class Logger(Thread):
    def __init__(self, stop_event, records_loggers, record_queue, msg_logger=None):
        """ Logger constructor

        :param stop_event: event that stops the logger
        :param records_loggers: {channel_name: records_logger, ...}
        :param record_queue: queue where to read records
        :param msg_logger: message logger for execution trace or debug
        """
        Thread.__init__(self)
        self.stop_event = stop_event
        self.__records_loggers = records_loggers
        self.record_queue = record_queue
        self.msg_logger = msg_logger

    @property
    def records_loggers(self):
        """ Gets and sets channels loggers
        """
        return self.__records_loggers

    @records_loggers.setter
    def records_loggers(self, val):
        self.__records_loggers = val

    def run(self):
        while not self.stop_event.isSet():
            try:
                record = self.record_queue.get(timeout=1.0)
                if record is not None:
                    print(record)
                    ch_id = record['tags']['channel']
                    cl = self.records_loggers[ch_id]
                    cl.log()
            except queue.Empty:
                pass


if __name__ == '__main__':
    sample_queue = queue.Queue()
    record_queue = queue.Queue()
    try:
        s = TempSensor()
        sensors = s.get_available_sensors()
    except:
        sensors = generate_w1temp_sensors(7)
    stop = Event()
    sampler = W1Sampler(stop_event=stop, interval=5, sensors=sensors, sample_queue=sample_queue)
    samples_conditioners = generate_w1temp_sensor_samples_conditioners(sensors=sensors)
    records_loggers = generate_w1temp_sensor_records_loggers()
    conditioner = Conditioner(stop_event=stop, samples_conditioners=samples_conditioners, sample_queue=sample_queue,
                              record_queue=record_queue)
    logger = Logger(stop_event=stop, records_loggers=records_loggers, record_queue=record_queue)
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
            print(record_queue.get(timeout=0.1))
        except queue.Empty:
            empty_queue = True
