#! /usr/bin/env python

import pickle

import numpy as np
import matplotlib.pyplot as plt
from keras.preprocessing.sequence import pad_sequences

from utility_functions import save_dataset_in_pickle
from constants import GESTURE, X_PICKLE_FILE, Y_PICKLE_FILE, MODEL_WEIGHTS_FILE

from sklearn.cluster import DBSCAN


def read_train_data(refresh_data=False):
    if refresh_data:
        save_dataset_in_pickle(X_PICKLE_FILE, Y_PICKLE_FILE)

    with open(X_PICKLE_FILE, 'rb') as f:
        X = pickle.load(f)

    with open(Y_PICKLE_FILE, 'rb') as f:
        Y = pickle.load(f)

    return X, Y


def padd_data(X, num_of_data_in_obj, max_num_of_objs, max_num_of_frames):
    padded_X = []

    # Pad objects
    zero_obj = [0.]*num_of_data_in_obj
    for sample in X:
        padded_sample = pad_sequences(sample, maxlen=max_num_of_objs,
                                      dtype='float32', padding='post',
                                      value=zero_obj)
        padded_X.append(padded_sample)

    # Pad frames
    zero_frame = [zero_obj for _ in range(max_num_of_objs)]
    padded_X = pad_sequences(padded_X, maxlen=max_num_of_frames,
                             dtype='float32', padding='post',
                             value=zero_frame)

    zero_frame = np.array(zero_frame)
    return np.array(padded_X)


def get_centeroid(arr):
    length = arr.shape[0]
    sum_x = np.sum(arr[:, 0])
    sum_y = np.sum(arr[:, 1])
    return sum_x/length, sum_y/length


if __name__ == '__main__':
    X, y = read_train_data()
    max_len = 0
    max_fidx = 0
    max_sidx = 0
    for s_idx, sample in enumerate(X):
        if len(sample) > 40:
            X[s_idx] = sample[:40]

    for s_idx, sample in enumerate(X):
        for f_idx, frame in enumerate(sample):
            frame = np.array(frame)
            db = DBSCAN(eps=0.1, min_samples=1).fit(frame[:, :2])
            n_clusters = len(set(db.labels_)) - (1 if -1 in db.labels_ else 0)
            clusters = [frame[:, :2][db.labels_ == i] for i in range(n_clusters)]
            new_xy = []
            for cluster in clusters:
                new_xy.append(get_centeroid(cluster))

            X[s_idx][f_idx] = np.array(X[s_idx][f_idx])
            X[s_idx][f_idx][:, :2] = new_xy[:]
