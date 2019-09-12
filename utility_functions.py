#! /usr/bin/env python

import os
import sys

from threading import Thread, Lock

import pickle
import pandas as pd

from constants import GESTURE


# Thread-safe print
_print = print
_print_lock = Lock()
def print(*args, **kwargs):
    _print_lock.acquire()
    try:
        _print(*args, **kwargs)
    finally:
        _print_lock.release()


# Thread wrapper
def threaded(fn):
    def wrapper(*args, **kwargs):
        thread = Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
        return thread
    return wrapper


def splitter(n, s):
    pieces = s.split(':')
    return (':'.join(pieces[i:i+n]) for i in range(0, len(pieces), n))


def warning(msg, rec, exp):
    print(msg, end=' ')
    print('Received \'' + rec + '\', ', end='')
    print('expected \'' + exp + '\'.')
    print('Packet dropped.')
    print()


def get_last_sample(gesture):
    save_dir = GESTURE.get_dir(gesture)
    if save_dir[-1] != '/':
        save_dir = save_dir + '/'

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

    return save_dir + last_sample


def get_data(gesture):
    save_dir = GESTURE.get_dir(gesture)
    if save_dir[-1] != '/':
        save_dir = save_dir + '/'

    print_cnt = 0
    for f in os.listdir(save_dir):
        df = pd.read_csv(save_dir + f)
        num_of_frames = df.iloc[-1]['frame'] + 1
        sample = [[] for i in range(num_of_frames)]
        if print_cnt == 100:
            print('.', end='')
            sys.stdout.flush()
            print_cnt = 0
        else:
            print_cnt += 1

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


def save_dataset_in_pickle(X_pickle_file, Y_pickle_file, max=100000):
    X = []
    Y = []

    gestures = GESTURE.get_all_gestures()

    print('\nRefreshing db', end='')
    for gesture in gestures:
        cnt = 0
        for sample in get_data(gesture):
            X.append(sample)
            Y.append(int(gesture))
            cnt += 1
            if cnt == max:
                break

    print('Done')

    with open(X_pickle_file, 'wb') as f:
        pickle.dump(X, f)

    with open(Y_pickle_file, 'wb') as f:
        pickle.dump(Y, f)
