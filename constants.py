#! /usr/bin/env python

from aenum import Constant


MAGIC_NUM = '02:01:04:03:06:05:08:07'
VERSION = '02.00.00.04'
PLATFORM = 'a1642'

X_PICKLE_FILE = '.X_data'
Y_PICKLE_FILE = '.Y_data'
MODEL_WEIGHTS_FILE = '.model_weights'


class STRUCT_TAG(Constant):
    DETECTED_POINTS = 1
    RANGE_PROFILE = 2
    NOISE_PROFILE = 3
    RANGE_AZIMUTH_HEAT_MAP = 4
    RANGE_DOPPLER_HEAT_MAP = 5
    STATS = 6


class GESTURE(Constant):
    SWIPE_UP = 0
    SWIPE_DOWN = 1
    SWIPE_LEFT = 2
    SWIPE_RIGHT = 3
    SPIN_CW = 4
    SPIN_CCW = 5
    LETTER_Z = 6
    LETTER_S = 7
    LETTER_X = 8

    @staticmethod
    def to_str(GESTURE_TAG):
        if GESTURE_TAG == GESTURE.SWIPE_UP:
            return 'Swipe Up'
        elif GESTURE_TAG == GESTURE.SWIPE_DOWN:
            return 'Swipe Down'
        elif GESTURE_TAG == GESTURE.SWIPE_LEFT:
            return 'Swipe Left'
        elif GESTURE_TAG == GESTURE.SWIPE_RIGHT:
            return 'Swipe Right'
        elif GESTURE_TAG == GESTURE.SPIN_CW:
            return 'Spin CW'
        elif GESTURE_TAG == GESTURE.SPIN_CCW:
            return 'Spin CCW'
        elif GESTURE_TAG == GESTURE.LETTER_Z:
            return 'Letter Z'
        elif GESTURE_TAG == GESTURE.LETTER_S:
            return 'Letter S'
        elif GESTURE_TAG == GESTURE.LETTER_X:
            return 'Letter X'
        else:
            return None

    @staticmethod
    def get_dir(GESTURE_TAG):
        if GESTURE_TAG == GESTURE.SWIPE_UP:
            return './data/swipe_up/'
        elif GESTURE_TAG == GESTURE.SWIPE_DOWN:
            return './data/swipe_down/'
        elif GESTURE_TAG == GESTURE.SWIPE_LEFT:
            return './data/swipe_left/'
        elif GESTURE_TAG == GESTURE.SWIPE_RIGHT:
            return './data/swipe_right/'
        elif GESTURE_TAG == GESTURE.SPIN_CW:
            return './data/spin_cw/'
        elif GESTURE_TAG == GESTURE.SPIN_CCW:
            return './data/spin_ccw/'
        elif GESTURE_TAG == GESTURE.LETTER_S:
            return './data/letter_s/'
        elif GESTURE_TAG == GESTURE.LETTER_Z:
            return './data/letter_z/'
        elif GESTURE_TAG == GESTURE.LETTER_X:
            return './data/letter_x/'
        else:
            return None

    @staticmethod
    def get_all_gestures():
        return [getattr(GESTURE, attr) for attr in dir(GESTURE)
                    if not attr.startswith("__")
                        and isinstance(getattr(GESTURE, attr), int)]

    @staticmethod
    def num_of_gestures():
        return len(GESTURE.get_all_gestures)
