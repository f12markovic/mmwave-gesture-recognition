#! /usr/bin/env python

import os
import time
import pickle

import pandas as pd
from tqdm import tqdm

from mmwave.data.formats import GESTURE
from mmwave.utils.utility_functions import print

import colorama
from colorama import Fore
colorama.init(autoreset=True)


class Logger():
    def __init__(self, GESTURE_TAG):
        self.logging = False
        self.gesture = GESTURE_TAG
        self.log_file = ''
        self.detected_time = 0
        self.empty_frames = ''
        self.frame_num = 0

    def __set_file(self):
        last_sample = self.get_last_sample(self.gesture)
        if last_sample[-1] == '/':
            self.log_file = last_sample + 'sample_1.csv'
        else:
            save_dir = '/'.join(last_sample.split('/')[:-1])
            last_sample_name = (last_sample.split('/')[-1]).split('.')[0]
            num = int(last_sample_name.split('_')[1]) + 1
            current_sample_name = '/sample_' + str(num) + '.csv'
            self.log_file = save_dir + current_sample_name
            print('Sample number: ' + str(num))

    def set_gesture(self, GESTURE_TAG):
        self.gesture = GESTURE_TAG

    def log(self, frame):
        if not self.logging:
            self.__set_file()
            self.logging = True
            self.detected_time = time.time()
            print('Saving...')

        if (frame is not None and
                frame.get('tlvs') is not None and
                frame['tlvs'].get(1) is not None):
            self.detected_time = time.time()
            with open(self.log_file, 'a') as f:
                if self.frame_num == 0:
                    f.write('frame,x,y,range_idx,peak_value,doppler_idx,xyz_q_format\n')

                for obj in frame['tlvs'][1]['values']['objs']:
                    f.write(self.empty_frames)
                    f.write(str(self.frame_num) + ',')
                    f.write(str(obj['x_coord']) + ',')
                    f.write(str(obj['y_coord']) + ',')
                    f.write(str(obj['range_idx']) + ',')
                    f.write(str(obj['peak_value']) + ',')
                    f.write(str(obj['doppler_idx']) + ',')
                    f.write(str(frame['tlvs'][1]['values']['descriptor']['xyz_q_format']) + '\n')
                    self.empty_frames = ''

            self.frame_num += 1

        elif self.frame_num != 0:
            self.empty_frames = (self.empty_frames +
                                   str(self.frame_num) + ',')
            self.empty_frames = (self.empty_frames +
                                   'None, None, None, None, None\n')
            self.frame_num += 1

        if time.time() - self.detected_time > 0.5:
            if os.path.isfile(self.log_file):
                print('Sample saved.\n')
            else:
                print('Nothing to save.\n')
            self.empty_frames = ''

            self.logging = False
            self.frame_num = 0
            return True

        return False

    @staticmethod
    def get_last_sample(gesture):
        save_dir = GESTURE.get_dir(gesture)

        if os.listdir(save_dir) == []:
            last_sample = ''
        else:
            nums = []
            for f in os.listdir(save_dir):
                num = f.split('.')[0]
                num = num.split('_')[1]
                nums.append(int(num))
            nums.sort()
            last_sample = 'sample_' + str(nums[-1]) + '.csv'

        return os.path.join(save_dir, last_sample)

    def discard_last_sample(self):
        last_sample = self.get_last_sample(self.gesture)
        if last_sample[-1] != '/':
            os.remove(last_sample)
            print('File deleted.')
        else:
            print('No files.')

    @staticmethod
    def get_data(gesture):
        save_dir = GESTURE.get_dir(gesture)
        for f in tqdm(os.listdir(save_dir), desc='Files', leave=False):
            df = pd.read_csv(os.path.join(save_dir, f))
            num_of_frames = df.iloc[-1]['frame'] + 1
            sample = [[] for i in range(num_of_frames)]

            for idx, row in df.iterrows():
                if row['x'] == 'None':
                    obj = [0., 0., 0., 0., 0.]
                else:
                    obj = [
                        float(row['x'])/65535.,
                        float(row['y'])/65535.,
                        float(row['range_idx'])/65535.,
                        float(row['peak_value'])/65535.,
                        float(row['doppler_idx'])/65535.
                    ]
                sample[row['frame']].append(obj)

            yield sample

    @staticmethod
    def get_all_data(refresh_data=False):
        X_file = os.path.join(os.path.dirname(__file__), '.X_data')
        y_file = os.path.join(os.path.dirname(__file__), '.y_data')
        if refresh_data:
            X = []
            y = []
            for gesture in tqdm(GESTURE.get_all_gestures(), desc='Gestures'):
                for sample in Logger.get_data(gesture):
                    X.append(sample)
                    y.append(int(gesture))
            pickle.dump(X, open(X_file, 'wb'))
            pickle.dump(y, open(y_file, 'wb'))
        else:
            print('Loading cached data...', end='')
            X = pickle.load(open(X_file, 'rb'))
            y = pickle.load(open(y_file, 'rb'))
            print('%sDone.' % Fore.GREEN)
        return X, y
