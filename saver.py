#! /usr/bin/env python

import os
import time

from utility_functions import get_last_sample, print


class Saver():
    def __init__(self, parser):
        self.__parser = parser

        self.__saving = False
        self.__current_sample = ''
        self.__detected_time = 0
        self.__empty_frames = ''
        self.__saved_frame_num = 0

    def __set_file_path(self, GESTURE_TAG):
        last_sample = get_last_sample(GESTURE_TAG)
        if last_sample[-1] == '/':
            self.__current_sample = last_sample + 'sample_1.csv'
        else:
            save_dir = '/'.join(last_sample.split('/')[:-1])
            last_sample_name = (last_sample.split('/')[-1]).split('.')[0]
            num = int(last_sample_name.split('_')[1]) + 1
            current_sample_name = '/sample_' + str(num) + '.csv'
            self.__current_sample = save_dir + current_sample_name
            print('Sample number: ' + str(num))

    def save(self, GESTURE_TAG):
        if self.__saving is False:
            self.__set_file_path(GESTURE_TAG)

            self.__saving = True
            self.__detected_time = time.time()
            print('Saving...')

        self.__parser.lock_data()
        try:
            with open(self.__current_sample, 'a') as f:
                if self.__parser.get_detected_objs() is not None:
                    self.__detected_time = time.time()
                    if self.__saved_frame_num == 0:
                        f.write('frame,x,y,range_idx,peak_value,doppler_idx,xyz_q_format\n')

                    det_objs_struct = self.__parser.get_detected_objs()
                    for obj in det_objs_struct['obj']:
                        f.write(self.__empty_frames)
                        f.write(str(self.__saved_frame_num) + ',')
                        f.write(str(obj['x_coord']) + ',')
                        f.write(str(obj['y_coord']) + ',')
                        f.write(str(obj['range_idx']) + ',')
                        f.write(str(obj['peak_value']) + ',')
                        f.write(str(obj['doppler_idx']) + ',')
                        f.write(str(det_objs_struct['descriptor']['xyz_q_format']) + '\n')
                        self.__empty_frames = ''

                    self.__saved_frame_num = self.__saved_frame_num + 1

                elif self.__saved_frame_num != 0:
                    self.__empty_frames = (self.__empty_frames +
                                           str(self.__saved_frame_num) + ',')
                    self.__empty_frames = (self.__empty_frames +
                                           'None, None, None, None, None\n')
                    self.__saved_frame_num = self.__saved_frame_num + 1
        finally:
            self.__parser.unlock_data()

        if time.time() - self.__detected_time > 0.5:
            if os.stat(self.__current_sample).st_size == 0:
                os.remove(self.__current_sample)
                print('Nothing to save.')
            else:
                print('Sample saved.')
            self.__empty_frames = ''
            print()

            self.__saving = False
            self.__detected_time = time.time()
            self.__saved_frame_num = 0
            return True

        return False

    def is_saving(self):
        return self.__saving

    def discard_last_sample(self, GESTURE_TAG):
        last_sample = get_last_sample(GESTURE_TAG)
        if last_sample[-1] != '/':
            os.remove(last_sample)
            print('File deleted.')
        else:
            print('No files.')
