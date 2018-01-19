import time
import os
import logging.handlers as handlers
import zipfile


class CompressedSizedTimedRotatingFileHandler(handlers.TimedRotatingFileHandler):
    """
    Handler for logging to a set of files, which switches from one file
    to the next when the current file reaches a certain size, or at certain
    timed intervals
    """
    def __init__(self, filename, max_bytes=0, backup_count=0, encoding=None,
                 delay=0, when='h', interval=1, utc=False, zip_mode=zipfile.ZIP_DEFLATED):
        handlers.TimedRotatingFileHandler.__init__(self, filename=filename, when=when, interval=interval, utc=utc,
                                                   backupCount=backup_count, encoding=encoding, delay=delay)
        self.maxBytes = max_bytes
        self.zip_mode = zip_mode

    def shouldRollover(self, record):
        """
        Determine if rollover should occur.

        Basically, see if the supplied record would cause the file to exceed
        the size limit we have.
        """
        if self.stream is None:                 # delay was set...
            self.stream = self._open()
        if self.maxBytes > 0:                   # are we rolling over?
            msg = "%s\n" % self.format(record)
            self.stream.seek(0, 2)              # due to non-posix-compliant Windows feature
            if self.stream.tell() + len(msg) >= self.maxBytes:
                return True
        t = int(time.time())
        if t >= self.rolloverAt:
            return True
        return False

    def find_last_rotated_file(self):
        dir_name, base_name = os.path.split(self.baseFilename)
        file_names = os.listdir(dir_name)
        result = []
        prefix = '{}.2'.format(base_name)  # we want to find a rotated file with eg filename.2017-12-12... name
        for file_name in file_names:
            if file_name.startswith(prefix) and not file_name.endswith('.zip'):
                result.append(file_name)
        result.sort()
        return os.path.join(dir_name, result[0])

    def doRollover(self):
        super(CompressedSizedTimedRotatingFileHandler, self).doRollover()

        dfn = self.find_last_rotated_file()
        dfn_zipped = '{}.zip'.format(dfn)
        if os.path.exists(dfn_zipped):
            os.remove(dfn_zipped)
        with zipfile.ZipFile(dfn_zipped, 'w', self.zip_mode) as f:
            f.write(dfn)
            print('zip ' + dfn)
        os.remove(dfn)
