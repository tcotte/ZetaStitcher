import queue
import argparse
import threading

import numpy as np
import pandas as pd

from .normxcorr import normxcorr2_fftw
from .filematrix import FileMatrix
from .inputfile import InputFile


def parse_args():
    parser = argparse.ArgumentParser(
        description='''
Stitch tiles in a folder.

The following naming conventions are used:
* Z is the direction along the stack height,
* (X, Y) is the frame plane,
* Y is the direction along which frames are supposed to overlap,
* X is the direction orthogonal to Y in the frame plane (X, Y).

Unless otherwise stated, all values are expected in px.
    ''',
        epilog='Author: Giacomo Mazzamuto <mazzamuto@lens.unifi.it>',
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument('input_folder', help='input folder')
    parser.add_argument('-c', type=str, default='g', choices=['r', 'g', 'b'],
                        dest='channel', help='color channel')

    group = parser.add_argument_group('tile ordering')

    group = parser.add_argument_group('maximum shifts')
    group.add_argument('--Mz', type=int, default=20, dest='max_dz',
                       help='maximum allowed shift along Z')

    group.add_argument('--My', type=int, default=150, dest='max_dy',
                       help='maximum allowed shift along Y (the stitching '
                            'axis)')

    group.add_argument('--Mx', type=int, default=20, dest='max_dx',
                       help='maximum allowed shift along X (lateral shift)')

    group = parser.add_argument_group('overlaps')
    group.add_argument('--overlap-h', type=int, default=600, metavar='OH',
                       help='overlap along the horizontal axis')

    group.add_argument('--overlap-v', type=int, default=600, metavar='OV',
                       help='overlap along the vertical axis')

    group = parser.add_argument_group(
        'multiple sampling along Z',
        description='Measure the optimal shift at different heights around '
                    'the center of the stack, then take the result with the '
                    'maximum score')
    group.add_argument('-a', action='store_true',
                       help='instead of maximum score, take the average '
                            'result weighted by the score',
                       dest='compute_average')

    group.add_argument('--z-samples', type=int, default=1, metavar='ZSAMP',
                       help='number of samples to take along Z')

    group.add_argument('--z-stride', type=int, default=200,
                       help='stride used for multiple Z sampling')

    parser.add_argument('-n', type=int, default=1,
                        help='number of parallel threads to use')

    args = parser.parse_args()

    channels = {
        'r': 0,
        'g': 1,
        'b': 2
    }

    args.channel = channels[args.channel]

    return args


class Runner(object):
    def __init__(self):
        self.channel = None
        self.q = None
        self.output_q = None
        self.data_queue = None
        self.initial_queue_length = None
        self.input_folder = None
        self.z_samples = None
        self.z_stride = None
        self.overlap_v = None
        self.overlap_h = None
        self.max_dx = None
        self.max_dy = None
        self.max_dz = None
        self.compute_average = False

    @property
    def overlap_dict(self):
        return {1: self.overlap_v, 2: self.overlap_h}

    def initialize_queue(self):
        fm = FileMatrix(self.input_folder)
        fm.ascending_tiles_X = True
        fm.ascending_tiles_Y = False

        group_generators = [fm.tiles_along_X, fm.tiles_along_Y]
        stitch_axis = [2, 1]

        q = queue.Queue()

        for group_generator, axis in zip(group_generators, stitch_axis):
            for group in group_generator:

                tile_generator = group.itertuples()

                atile = next(tile_generator)

                for btile in tile_generator:
                    central_frame = atile.nfrms // 2
                    start_frame = (
                        central_frame
                        - (self.z_samples // 2 * self.z_stride)
                        + (0 if self.z_samples % 2 else self.z_stride // 2))
                    for i in range(0, self.z_samples):
                        z_frame = start_frame + i * self.z_stride
                        params_dict = {
                            'aname': atile.filename,
                            'bname': btile.filename,
                            'z_frame': z_frame,
                            'axis': axis,
                        }
                        q.put(params_dict)
                    atile = btile
        self.q = q

    def worker(self, initial_queue_length):
        while True:
            item = self.data_queue.get()
            if item is None:
                break
            try:
                aname = item[0]
                bname = item[1]
                axis = item[2]
                alayer = item[3]
                blayer = item[4]
                z_frame = item[5]

                xcorr = normxcorr2_fftw(alayer, blayer)

                shift = list(np.unravel_index(np.argmax(xcorr), xcorr.shape))
                score = xcorr[tuple(shift)]

                print('{progress:.2f}%\t{aname}\t{bname}\t{z_frame}\t'
                      '{shift}\t{score}'.format(
                       progress=(
                           100 * (1 - self.q.qsize() / initial_queue_length)),
                       aname=aname, bname=bname, z_frame=z_frame, shift=shift,
                       score=score))
                self.output_q.put([aname, bname, axis] + shift + [score])
            finally:
                self.data_queue.task_done()
                self.q.task_done()

    def keep_filling_data_queue(self):
        while True:
            try:
                item = self.q.get_nowait()
            except queue.Empty:
                break
            aname = item['aname']
            bname = item['bname']
            z_frame = item['z_frame']
            axis = item['axis']
            overlap = self.overlap_dict[axis]

            a = InputFile(aname)
            b = InputFile(bname)

            a.channel = self.channel
            b.channel = self.channel

            z_min = z_frame - self.max_dz
            z_max = z_frame + self.max_dz + 1

            alayer = a.layer(z_min, z_max)
            if axis == 2:
                alayer = np.rot90(alayer, axes=(-2, -1))
            alayer = alayer[..., -overlap:, :]

            blayer = b.layer_idx(z_frame)
            if axis == 2:
                blayer = np.rot90(blayer, axes=(-2, -1))
            blayer = blayer[..., 0:overlap, :]

            blayer = blayer[
                ..., :-self.max_dy, self.max_dx:-self.max_dx]

            alayer = alayer.astype(np.float32)
            blayer = blayer.astype(np.float32)

            self.data_queue.put([aname, bname, axis, alayer, blayer, z_frame])

    def aggregate_results(self):
        df = pd.DataFrame(list(self.output_q.queue))
        df.columns = ['aname', 'bname', 'axis', 'dz', 'dy', 'dx', 'score']

        if self.compute_average:
            view = df.groupby(['aname', 'bname', 'axis']).agg(
                lambda x: np.average(x, weights=df.loc[x.index, 'score']))
        else:
            view = df.groupby(['aname', 'bname', 'axis']).agg(
                lambda x: df.loc[np.argmax(df.loc[x.index, 'score']), x.name])

        view = view.reset_index()

        view.dz -= self.max_dz
        for a in [1, 2]:
            indexes = (view['axis'] == a)
            view.loc[indexes, 'dy'] = \
                self.overlap_dict[a] - view.loc[indexes, 'dy']
        view.dx -= self.max_dx

        return view

    def run(self):
        self.initialize_queue()
        self.data_queue = queue.Queue(maxsize=int(arg.n * 2))
        self.output_q = queue.Queue()
        threads = []
        for i in range(arg.n):
            t = threading.Thread(target=self.worker, args=(self.q.qsize(),))
            t.start()
            threads.append(t)

        self.keep_filling_data_queue()

        # block until all tasks are done
        self.data_queue.join()

        # stop workers
        for i in range(arg.n):
            self.data_queue.put(None)
        for t in threads:
            t.join()

        view = self.aggregate_results()

        print(view)

        with open('stitch.json', 'w') as f:
            f.write(view.to_json(orient='records'))


if __name__ == '__main__':
    arg = parse_args()

    r = Runner()

    keys = ['input_folder', 'channel', 'max_dx', 'max_dy', 'max_dz',
            'z_samples', 'z_stride', 'overlap_v', 'overlap_h',
            'compute_average']
    for key in keys:
        setattr(r, key, getattr(arg, key))

    r.run()
