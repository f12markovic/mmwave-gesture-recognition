#! /usr/bin/env python

import os
import time
import pickle

import numpy as np

from sklearn.model_selection import train_test_split

#  Disable tensorflow logs
import logging
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

import tensorflow as tf
from tensorflow.keras import Model
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.layers import Input, Dense, Dropout, PReLU, GlobalAveragePooling1D
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping
from tensorflow.keras.models import load_model

from mmwave.model.transformer import TransformerBlock
from mmwave.data.formats import GESTURE
from mmwave.data.logger import Logger

logger = tf.get_logger()
logger.disabled = True
logger.setLevel(logging.FATAL)

import colorama
from colorama import Fore
colorama.init(autoreset=True)


class NN:
    def __init__(self):
        self.collecting = False
        self.sequence = []
        self.frame_num = 0
        self.empty_frames = []
        self.detected_time = 0

        self.model = None
        self.model_weights = os.path.join(os.path.dirname(__file__),
                                          '.model_weights')
        self.weights_loaded = False
        self.max_num_of_frames = 50
        self.max_num_of_objs = 65
        self.num_of_data_in_obj = 5
        self.num_of_classes = 9

        self.X = None
        self.y = None

    def __get_data(self, refresh_data=False):
        self.X, self.y = Logger.get_all_data(refresh_data)

        self.__get_stats()
        self.__prep_data()

    def __get_stats(self):
        self.num_of_classes = len(set(self.y))
        print('Number of classes: ' + str(self.num_of_classes))
        sample_with_max_num_of_frames = max(self.X,
                                            key=lambda sample: len(sample))
        if self.max_num_of_frames is None:
            self.max_num_of_frames = len(sample_with_max_num_of_frames)
        print('Maximum number of frames: ' + str(self.max_num_of_frames))

        sample_with_max_num_of_objs = max(
            self.X, key=lambda sample: [len(frame) for frame in sample]
        )

        frame_with_max_num_of_objs = max(
            sample_with_max_num_of_objs, key=lambda obj: len(obj)
        )
        if self.max_num_of_objs is None:
            self.max_num_of_objs = len(frame_with_max_num_of_objs)
        print('Maximum num of objects: ' + str(self.max_num_of_objs))

    def __padd_data(self, data):
        padded_data = []

        # Pad objects
        zero_obj = [0.]*self.num_of_data_in_obj
        for sample in data:
            if len(sample) > self.max_num_of_objs:
                sample = sample[:self.max_num_of_objs]
            padded_sample = pad_sequences(sample, maxlen=self.max_num_of_objs,
                                          dtype='float32', padding='post',
                                          value=zero_obj)
            padded_data.append(padded_sample)

        # Pad frames
        zero_frame = [zero_obj for _ in range(self.max_num_of_objs)]
        padded_data = pad_sequences(padded_data, maxlen=self.max_num_of_frames,
                                    dtype='float32', padding='post',
                                    value=zero_frame)

        return np.asarray(padded_data)

    def __prep_data(self):
        # X has been already normalized while importing the data from .csv files
        self.X = self.__padd_data(self.X)
        frame_size = self.max_num_of_objs*self.num_of_data_in_obj
        self.X = self.X.reshape((len(self.X),
                                 self.max_num_of_frames,
                                 frame_size))

        # One hot encoding of y
        self.y = to_categorical(self.y)

    def __create_model(self):
        frame_size = self.max_num_of_objs*self.num_of_data_in_obj

        inputs = Input(shape=(self.max_num_of_frames, frame_size,))

        x = TransformerBlock(frame_size=frame_size,
                             num_heads=25, units=512, dropout=0.5)(inputs)
        x = GlobalAveragePooling1D()(x)
        x = Dropout(0.5)(x)

        x = Dense(128)(x)
        x = PReLU()(x)
        x = Dropout(0.5)(x)

        outputs = Dense(self.num_of_classes, activation='softmax')(x)

        self.model = Model(inputs=inputs, outputs=outputs)
        self.model.compile(loss='categorical_crossentropy',
                           optimizer='adam',
                           metrics=['accuracy'])
        self.model.summary()

    def train(self, refresh_data=False):
        self.__get_data(refresh_data=refresh_data)
        self.__create_model()
        self.weights_loaded = False

        X_train, X_val, y_train, y_val = train_test_split(self.X, self.y,
                                                          stratify=self.y,
                                                          test_size=0.3)

        history = self.model.fit(X_train, y_train, epochs=1000,
                                 validation_data=(X_val, y_val),
                                 callbacks=[EarlyStopping(patience=20),
                                            ModelCheckpoint(self.model_weights,
                                                            save_best_only=True)])
        pickle.dump(history, open('.history', 'wb'))

    def load_model(self):
        print('Loading weights...', end='')
        self.model = load_model(self.model_weights)
        self.weights_loaded = True
        print('%sDone.' % Fore.GREEN)

    def evaluate(self, refresh_data=False):
        self.__get_data(refresh_data=refresh_data)

        if not self.weights_loaded:
            self.load_model()

        preds = self.model.evaluate(self.X, self.y)
        print('Loss: ' + str(round(preds[0], 4)), end=' ')
        print('Acc: ' + str(round(preds[1], 4)))

    def set_sequence(self, frame):
        if self.collecting is False:
            self.collecting = True
            self.sequence = []
            self.detected_time = time.time()

        if (frame is not None and
                frame.get('tlvs') is not None and
                frame['tlvs'].get(1) is not None):
            self.detected_time = time.time()
            if self.frame_num == 0:
                self.sequence = []

            for empty_frame in self.empty_frames:
                self.sequence.append(empty_frame)
                self.empty_frames = []

            objs = []
            for obj in frame['tlvs'][1]['values']['objs']:
                if obj is None or None in obj.values():
                    continue
                objs.append([
                    obj['x_coord']/65535.,
                    obj['y_coord']/65535.,
                    obj['range_idx']/65535.,
                    obj['peak_value']/65535.,
                    obj['doppler_idx']/65535.
                ])
            self.sequence.append(objs)
            self.frame_num += 1

            if self.frame_num >= self.max_num_of_frames:
                self.empty_frames = []
                self.collecting = False
                self.frame_num = 0
                return True

        elif self.frame_num != 0:
            self.empty_frames.append([[0.]*self.num_of_data_in_obj])
            self.frame_num += 1

        if time.time() - self.detected_time > 0.5:
            self.empty_frames = []
            self.collecting = False
            self.frame_num = 0
            return True

        return False

    def predict(self, debug=False):
        if len(self.sequence) <= 3:
            return

        X = self.__padd_data([self.sequence])
        X = X.reshape((1,
                       self.max_num_of_frames,
                       self.max_num_of_objs*self.num_of_data_in_obj))

        y_pred = self.model.predict(X)
        item = y_pred[0]
        best_guess = [item.tolist().index(x) for x in sorted(item, reverse=True)]
        best_value = sorted(item, reverse=True)

        if debug:
            for guess, val in zip(best_guess, best_value):
                print('%sBest guess: ' % Fore.YELLOW + GESTURE.to_str(guess)
                       + ': %.2f%%' % val)
            print('%s------------------------------\n' % Fore.CYAN)

        if best_value[0] >= 0.9:
            print('%sGesture recognized:' % Fore.GREEN)
            print(Fore.BLUE + GESTURE.to_str(best_guess[0]))
            print('%s==============================\n' % Fore.CYAN)
