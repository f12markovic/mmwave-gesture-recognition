#! /usr/bin/env python

import numpy as np
import pandas as pd

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.animation as animation

from utility_functions import get_last_sample


# Global plot config
mpl.rcParams['toolbar'] = 'None'
plt.style.use('seaborn-dark')


class Plotter:
    def __init__(self, parser):
        self.__parser = parser
        self.__gesture = 0

        self.__redrawing = False
        self.__redraw_init = False
        self.__last_sample_gen = None

        self.__fig = plt.figure()
        ax = self.__fig.add_subplot(111)
        ax.grid(b=False)

        self.__sc = ax.scatter([], [], color='r')
        plt.xticks(np.arange(-100, 101, step=25),
                   ('-1m', '-0.75m', '-0.5m', '-0.25m',
                      '0', '+0.25m', '+0.5m', '+0.75m', '1m'))
        plt.yticks(np.arange(0, 201, step=40),
                   ('0', '0.25m', '0.5m', '0.75m', '1m', '1.25m'))

        ax.set_xlim(-100, 100)
        ax.set_ylim(0, 200)

        axes_coords = [-0.2574, -0.6612, 1.54, 1.54]

        ax_polar = self.__fig.add_axes(axes_coords, projection='polar')
        ax_polar.patch.set_alpha(0)
        ax_polar.set_yticklabels([])
        self.__sc.set_color([1, 0, 0])

    def __get_previos_data(self):
        last_sample = get_last_sample(self.__gesture)
        if last_sample[-1] == '/':
            yield None

        df = pd.read_csv(last_sample).reset_index().values

        num_of_frames = df[-1][1]+1
        points = [[] for i in range(num_of_frames)]
        for row in df:
            if row[2] == 'None' or row[3] == 'None':
                points[row[1]].append((None, None))
            else:
                new_x, new_y = int(row[2]), int(row[3])
                if new_x > 32767:
                    new_x = new_x - 65536

                if new_y > 32767:
                    new_y = new_y - 65536

                new_x = new_x/int(row[7])
                new_y = new_y/int(row[7])

                if -100 <= new_x <= 100 and 0 <= new_y <= 100:
                    points[row[1]].append((new_x, new_y))

        for frame in points:
            yield frame

    def redraw(self, GESTURE_TAG):
        self.__gesture = GESTURE_TAG
        self.__redrawing = True

    def __update_det_objs(self, data):
        x, y = [], []
        objs = self.__parser.get_detected_objs()
        if self.__redrawing is True:
            if self.__redraw_init is False:
                self.__sc.set_color([0.5, 0.5, 0.5])
                self.__last_sample_gen = self.__get_previos_data()

                self.__redraw_init = True
                print('Redrawing...')
            try:
                frame = next(self.__last_sample_gen)
                if frame is None:
                    self.__redrawing = False
                    self.__redraw_init = False
                    self.__sc.set_color([1, 0, 0])
                    print('No files.')
                    return
                for new_x, new_y in frame:
                    x.append(new_x)
                    y.append(new_y)

            except StopIteration:
                print('Done')
                self.__sc.set_color([1, 0, 0])
                self.__redraw_init = False
                self.__redrawing = False

        elif objs is not None:
            for o in objs['obj']:
                new_x, new_y = o['x_coord'], o['y_coord']
                if new_x > 32767:
                    new_x = new_x - 65536

                if new_y > 32767:
                    new_y = new_y - 65536

                new_x = new_x/objs['descriptor']['xyz_q_format']
                new_y = new_y/objs['descriptor']['xyz_q_format']

                if -100 <= new_x <= 100 and 0 <= new_y <= 100:
                    x.append(new_x)
                    y.append(new_y)

        self.__sc.set_offsets(np.c_[x, y])

    def is_redrawing(self):
        return self.__redrawing

    def plot_detected_objs(self):
        ani = animation.FuncAnimation(self.__fig, self.__update_det_objs,
                                      frames=2, interval=10, repeat=True)
        plt.show()
