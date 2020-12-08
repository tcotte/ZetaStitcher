# Suppress warnings when importing pims on a machine without display server
# The warnings are due to import matplotlib.pyplot as plt in pim's display.py
import matplotlib as mpl
mpl.use('Agg')

from pims import ImageSequence

from zetastitcher.io.inputfile_mixin import InputFileMixin


class PimsWrapper(InputFileMixin):
    def __init__(self, initializer=None):
        super().__init__()

        self.initializer = initializer
        self.imseq = None

        if self.initializer is not None:
            self.open()

    def open(self, initializer=None):
        if initializer is not None:
            self.initializer = initializer

        self.imseq = ImageSequence(str(self.initializer))
        setattr(self, 'close', getattr(self.imseq, 'close'))

        self.nfrms = len(self.imseq)
        self.ysize = self.imseq.frame_shape[0]
        self.xsize = self.imseq.frame_shape[1]
        self.dtype = self.imseq._dtype

        if len(self.imseq.frame_shape) > 2:
            self.nchannels = self.imseq.frame_shape[2]

    def frame(self, index, dtype=None):
        a = self.imseq[index]
        if dtype is not None:
            a = a.astype(dtype)
        return a
