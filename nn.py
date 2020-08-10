#! /usr/bin/env python

import os
import time
import argparse

import pickle
from utility_functions import save_dataset_in_pickle

import numpy as np
import matplotlib.pyplot as plt

from sklearn.model_selection import train_test_split

# Disable tensorflow logs
import logging
logging.getLogger('tensorflow').disabled = True


from tensorflow.keras import Model
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.preprocessing.sequence import pad_sequences
from tensorflow.keras.layers import Input, Dense, Dropout, PReLU, GlobalAveragePooling1D
from tensorflow.keras.callbacks import ModelCheckpoint, EarlyStopping
from tensorflow.keras.models import load_model

from transformer import TransformerBlock

from constants import GESTURE, X_PICKLE_FILE, Y_PICKLE_FILE, MODEL_WEIGHTS_FILE


class NN():
    def __init__(self, parser, refresh_data=False):
        self.__parser = parser

        self.__collecting_frame = False
        self.__current_sample = []
        self.__detected_time = 0
        self.__empty_frames = []
        self.__saved_frame_num = 0

        self.__model = None

        self.__X = []
        self.__Y = []
        self.__zero_frame = []

        self.__read_train_data(refresh_data=refresh_data)
        self.__create_model()

    def __read_train_data(self, refresh_data=False):
        if refresh_data:
            save_dataset_in_pickle(X_PICKLE_FILE, Y_PICKLE_FILE)

        with open(X_PICKLE_FILE, 'rb') as f:
            self.__X = pickle.load(f)

        with open(Y_PICKLE_FILE, 'rb') as f:
            self.__Y = pickle.load(f)

        self.__get_stats()
        self.__data_prep()

    def __get_stats(self):
        self.__num_of_data_in_obj = 5

        self.__K = len(set(self.__Y))
        print('Number of classes: ' + str(self.__K))

        #  sample_with_max_num_of_frames = max(self.__X, key=lambda sample: len(sample))
        #  self.__max_num_of_frames = len(sample_with_max_num_of_frames)
        self.__max_num_of_frames = 50
        print('Maximum number of frames: ' + str(self.__max_num_of_frames))

        sample_with_max_num_of_objs = max(
            self.__X, key=lambda sample: [len(frame) for frame in sample]
        )
        frame_with_max_num_of_objs = max(
            sample_with_max_num_of_objs, key=lambda obj: len(obj)
        )
        self.__max_num_of_objs = len(frame_with_max_num_of_objs)
        print('Maximum num of objects: ' + str(self.__max_num_of_objs))

    def __padd_data(self, X):
        padded_X = []

        # Pad objects
        zero_obj = [0.]*self.__num_of_data_in_obj
        for sample in X:
            if len(sample) > 50:
                sample = sample[:50]
            padded_sample = pad_sequences(sample, maxlen=self.__max_num_of_objs,
                                          dtype='float32', padding='post',
                                          value=zero_obj)
            padded_X.append(padded_sample)

        # Pad frames
        self.__zero_frame = [zero_obj for _ in range(self.__max_num_of_objs)]
        padded_X = pad_sequences(padded_X, maxlen=self.__max_num_of_frames,
                                 dtype='float32', padding='post',
                                 value=self.__zero_frame)

        self.__zero_frame = np.asarray(self.__zero_frame)
        return np.asarray(padded_X)

    def __data_prep(self):
        # X has been already normalized while importing the data from .csv files
        self.__X = self.__padd_data(self.__X)
        frame_size = self.__max_num_of_objs*self.__num_of_data_in_obj
        self.__X = self.__X.reshape((len(self.__X),
                                     self.__max_num_of_frames,
                                     frame_size))

        # One hot enocding of Y
        self.__Y = to_categorical(self.__Y)

    def __create_model(self):
        frame_size = self.__max_num_of_objs*self.__num_of_data_in_obj

        inputs = Input(shape=(self.__max_num_of_frames, frame_size,))

        x = TransformerBlock(frame_size=frame_size,
                             num_heads=25, units=512, dropout=0.5)(inputs)
        x = GlobalAveragePooling1D()(x)
        x = Dropout(0.5)(x)

        x = Dense(128)(x)
        x = PReLU()(x)
        x = Dropout(0.5)(x)

        outputs = Dense(self.__K, activation='softmax')(x)

        self.__model = Model(inputs=inputs, outputs=outputs)
        self.__model.compile(loss='categorical_crossentropy',
                             optimizer='adam',
                             metrics=['accuracy'])
        self.__model.summary()

    def look_into_data(self):
        i = 1
        # Plot each column
        fig = plt.figure()
        while True:
            seed = np.random.randint(len(self.__X))
            for data_in_obj in range(self.__num_of_data_in_obj):
                plt.subplot(self.__num_of_data_in_obj, 1, i)
                plt.plot(self.__X[seed][:, data_in_obj])
                if data_in_obj == 0:
                    plt.title('x ', y=0.5, loc='right')
                elif data_in_obj == 1:
                    plt.title('y ', y=0.5, loc='right')
                elif data_in_obj == 2:
                    plt.title('range_idx ', y=0.5, loc='right')
                elif data_in_obj == 3:
                    plt.title('peak_value ', y=0.5, loc='right')
                elif data_in_obj == 4:
                    plt.title('doppler_idx ', y=0.5, loc='right')
                else:
                    plt.title('Unknown ', y=0.5, loc='right')
                fig.suptitle(GESTURE.to_str(np.argmax(self.__Y[seed])), fontsize=16)
                i += 1
            i = 1
            plt.show()

    def train(self):
        X_train, X_val, y_train, y_val = train_test_split(self.__X, self.__Y,
                                                          stratify=self.__Y,
                                                          test_size=0.3)

        history = self.__model.fit(X_train, y_train, epochs=1000,
                                   validation_data=(X_val, y_val),
                                   callbacks=[EarlyStopping(patience=20),
                                              ModelCheckpoint(MODEL_WEIGHTS_FILE,
                                                              save_best_only=True)])
        with open('.history', 'wb') as f:
            pickle.dump(history, f)

    def load_model(self):
        print('Loading weights...', end='')
        self.__model = load_model(MODEL_WEIGHTS_FILE)
        print('Done.')

    def evaluate(self):
        preds = self.__model.evaluate(self.__X, self.__Y)
        print('Loss: ' + str(round(preds[0], 4)), end=' ')
        print('Acc: ' + str(round(preds[1], 4)))

    def get_data(self):
        if self.__collecting_frame is False:
            self.__parser.lock_data()
            try:
                if self.__parser.get_detected_objs() is not None:
                    self.__collecting_frame = True
                    self.__detected_time = time.time()
            finally:
                self.__parser.unlock_data()

        self.__parser.lock_data()
        try:
            if self.__parser.get_detected_objs() is not None:
                self.__detected_time = time.time()
                if self.__saved_frame_num == 0:
                    self.__current_sample = []
                init = False
                det_objs_struct = self.__parser.get_detected_objs()
                for obj in det_objs_struct['obj']:
                    if self.__empty_frames != []:
                        for empty_frame in self.__empty_frames:
                            self.__current_sample.append(empty_frame)
                            self.__empty_frames = []

                    if init is False:
                        self.__current_sample.append([])
                        init = True
                    self.__current_sample[self.__saved_frame_num].append([
                        float(obj['x_coord'])/65535.,
                        float(obj['y_coord'])/65535.,
                        float(obj['range_idx'])/65535.,
                        float(obj['peak_value'])/65535.,
                        float(obj['doppler_idx'])/65535.
                    ])

                self.__saved_frame_num = self.__saved_frame_num + 1
                if len(self.__current_sample) >= self.__max_num_of_frames:
                    self.__empty_frames = []
                    self.__collecting_frame = False
                    self.__detected_time = time.time()
                    self.__saved_frame_num = 0
                    return True

            elif self.__saved_frame_num != 0:
                self.__empty_frames.append([[0.]*self.__num_of_data_in_obj])
                self.__saved_frame_num = self.__saved_frame_num + 1
        finally:
            self.__parser.unlock_data()

        if time.time() - self.__detected_time > 0.5:
            self.__empty_frames = []
            self.__collecting_frame = False
            self.__detected_time = time.time()
            self.__saved_frame_num = 0
            return True

        return False

    def predict(self, debug=False):
        if len(self.__current_sample) >= 4:
            X = []
            X.append(self.__current_sample)

            X = self.__padd_data(X)
            X = X.reshape((1,
                           self.__max_num_of_frames,
                           self.__max_num_of_objs*self.__num_of_data_in_obj))

            self.__current_sample = []

            Y_pred = self.__model.predict(X)
            item = Y_pred[0]
            best_guess = [item.tolist().index(x) for x in sorted(item, reverse=True)[:3]]
            best_value = sorted(item, reverse=True)[:3]
            if debug:
                print('Best guess: ' + GESTURE.to_str(best_guess[0])
                       + ': %.2f%%' % best_value[0])
                print('Best guess: ' + GESTURE.to_str(best_guess[1])
                       + ': %.2f%%' % best_value[1])
                print('Best guess: ' + GESTURE.to_str(best_guess[2])
                       + ': %.2f%%' % best_value[2])
                print('------------------------------')
                print()
            if best_value[0] >= 0.95:
                print('Gesture recognized:')
                print(GESTURE.to_str(best_guess[0]))
                print('==============================')
                print()


def parse_args():
    print()
    argparser = argparse.ArgumentParser(description='Training and evaluating \
                                                     neural network.')
    argparser.add_argument('input', type=str, help='Select eval or train')
    argparser.add_argument(
        '-r',
        '--refresh_db',
        action='store_false',
        help='refresh database'
    )

    args = argparser.parse_args()
    return args


if __name__ == '__main__':
    args = parse_args()

    if args.input == 'train':
        training = True
    elif args.input == 'eval':
        training = False
    else:
        print('Unknown input \"' + args.input + '\".')
        exit()

    if args.refresh_db is True:
        nn = NN(None)
    else:
        nn = NN(None, refresh_data=True)

    if training:
        nn.train()
    else:
        nn.load_model()
        nn.evaluate()
