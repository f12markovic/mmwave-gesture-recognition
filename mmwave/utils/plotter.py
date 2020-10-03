#! /usr/bin/env python

import time

import numpy as np
import pandas as pd

import matplotlib as mpl
import matplotlib.pyplot as plt

from mmwave.data.logger import Logger


# Global plot config
mpl.rcParams['toolbar'] = 'None'
plt.style.use('seaborn-dark')


class Plotter:
    def __init__(self, queue):
        self.xy = []

        self.queue = queue

        self.fig = None
        self.ax = None
        self.sc = None

        self.__set_figure()

        self.background = self.fig.canvas.copy_from_bbox(self.ax.bbox)
        connect = self.fig.canvas.mpl_connect
        self.draw_cid = connect('draw_event', self.__grab_background)
        connect('close_event', self.__fig_close)

    def __set_figure(self):
        self.fig, self.ax = plt.subplots()
        self.sc = self.ax.scatter([], [], color='r', picker=10, animated=True)

        self.ax.grid(b=False)
        plt.xticks(np.arange(-100, 101, step=25),
                   ('-1m', '-0.75m', '-0.5m', '-0.25m',
                      '0', '+0.25m', '+0.5m', '+0.75m', '1m'))
        plt.yticks(np.arange(0, 201, step=40),
                   ('0', '0.25m', '0.5m', '0.75m', '1m', '1.25m'))
        self.ax.set_xlim(-100, 100)
        self.ax.set_ylim(0, 200)

        axes_coords = [-0.2574, -0.6612, 1.54, 1.54]

        ax_polar = self.fig.add_axes(axes_coords, projection='polar')
        ax_polar.patch.set_alpha(0)
        ax_polar.set_yticklabels([])
        self.sc.set_color([1, 0, 0])

    def __grab_background(self, event=None):
        self.sc.set_visible(False)

        # Temporarily disconnect the draw_event callback to avoid recursion
        canvas = self.fig.canvas
        canvas.mpl_disconnect(self.draw_cid)
        canvas.draw()

        self.draw_cid = canvas.mpl_connect('draw_event', self.__grab_background)
        self.background = self.fig.canvas.copy_from_bbox(self.fig.bbox)
        self.sc.set_visible(True)
        self.__blit()

    def __fig_close(self, event=None):
        self.queue.put('closed')

    def __blit(self):
        self.fig.canvas.restore_region(self.background)
        self.ax.draw_artist(self.sc)
        self.fig.canvas.blit(self.ax.bbox)

    def __update(self):
        if self.xy == []:
            self.xy = [None, None]

        self.sc.set_offsets(self.xy)
        self.__blit()

    def __get_previos_data(self, gesture):
        last_sample = Logger.get_last_sample(gesture)
        if last_sample[-1] == '/':
            return None

        df = pd.read_csv(last_sample).reset_index().values

        num_of_frames = df[-1][1]+1
        points = [[] for i in range(num_of_frames)]
        for row in df:
            if row[2] == 'None' or row[3] == 'None':
                points[row[1]].append((None, None))
            else:
                x, y = int(row[2]), int(row[3])
                if x > 32767:
                    x = x - 65536

                if y > 32767:
                    y = y - 65536

                x = x/int(row[7])
                y = y/int(row[7])

                points[row[1]].append((x, y))
        return points

    def draw_last_sample(self, gesture):
        self.sc.set_color([0.5, 0.5, 0.5])
        last_sample = self.__get_previos_data(gesture)
        print('Redrawing...')

        self.xy = []
        self.__update()

        for frame in last_sample:
            self.xy = []
            for x, y in frame:
                self.xy.append([x, y])

            self.__update()
            time.sleep(0.03)

        print('Done')

        self.xy = []
        self.__update()
        self.sc.set_color([1, 0, 0])

    def plot_detected_objs(self, frame):
        self.xy = []

        if (frame is not None and
                frame.get('tlvs') is not None and
                frame['tlvs'].get(1) is not None):

            objs = frame['tlvs'][1]['values']['objs']
            desc = frame['tlvs'][1]['values']['descriptor']
            for obj in objs:
                if obj is None or None in obj.values():
                    continue

                x, y = obj['x_coord'], obj['y_coord']
                if x > 32767:
                    x = x - 65536

                if y > 32767:
                    y = y - 65536

                x = x/desc['xyz_q_format']
                y = y/desc['xyz_q_format']

                self.xy.append([x, y])

        self.__update()

    def show(self):
        plt.gcf().canvas.flush_events()
        plt.show(block=False)
        time.sleep(1)

    def close(self):
        plt.close()
