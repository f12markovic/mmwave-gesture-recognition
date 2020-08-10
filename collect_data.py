# /usr/bin/env python

import os
import time
import argparse

from parser import Parser
from saver import Saver
from plotter import Plotter
from connection import Connection
from utility_functions import threaded
from constants import GESTURE


CURRENT_GESTURE = None


# Functions
@threaded
def get_user_input(s, pl):
    time.sleep(0.5)
    while True:
        button = input('\nInput \'r\' to redraw last saved sample\n'
                       + 'Input \'d\' to delete last saved sample.\n'
                       + 'Input any other key to start saving new sample.\n')
        # Quit
        if button == 'q':
            os._exit(1)
        # Discard last sample and save
        elif button == 'd':
            s.discard_last_sample(CURRENT_GESTURE)
        # Redraw last sample
        elif button == 'r':
            pl.redraw(CURRENT_GESTURE)
            redrawing = True
            while redrawing:
                redrawing = pl.is_redrawing()
                time.sleep(0.05)
        # Save
        else:
            done = False
            while not done:
                done = s.save(CURRENT_GESTURE)
                time.sleep(0.05)
    time.sleep(0.1)


@threaded
def interpretor(c, p):
    while True:
        frame = c.getFrame()
        p.parse(frame)
        #  p.print_frame()
        c.readDone()
        time.sleep(0.01)


def parse_args():
    global CURRENT_GESTURE
    argparser = argparse.ArgumentParser(description='Collecting samples \
                                                     from mmWave')
    argparser.add_argument('gesture',
                           type=str,
                           help='Select one of the following gestures: up, \
                                 down, right, left, cw, ccw, z, x, s, spiral')
    args = argparser.parse_args()

    if args.gesture == 'up':
        CURRENT_GESTURE = GESTURE.SWIPE_UP
    elif args.gesture == 'down':
        CURRENT_GESTURE = GESTURE.SWIPE_DOWN
    elif args.gesture == 'right':
        CURRENT_GESTURE = GESTURE.SWIPE_RIGHT
    elif args.gesture == 'left':
        CURRENT_GESTURE = GESTURE.SWIPE_LEFT
    elif args.gesture == 'cw':
        CURRENT_GESTURE = GESTURE.SPIN_CW
    elif args.gesture == 'ccw':
        CURRENT_GESTURE = GESTURE.SPIN_CCW
    elif args.gesture == 'z':
        CURRENT_GESTURE = GESTURE.LETTER_Z
    elif args.gesture == 'x':
        CURRENT_GESTURE = GESTURE.LETTER_X
    elif args.gesture == 's':
        CURRENT_GESTURE = GESTURE.LETTER_S
    else:
        print('Unknown gesture.')
        exit()


if __name__ == '__main__':
    parse_args()

    ports = []
    while ports == []:
        ports = Connection.findPorts()
    conn = Connection(ports[0], ports[1])

    mmwave_configured = False
    while not mmwave_configured:
        mmwave_configured = conn.sendCfg('./profiles/profile.cfg')

    parser = Parser()
    #  parser = Parser(warn=True)
    saver = Saver(parser)
    plotter = Plotter(parser)

    interpretor(conn, parser)
    get_user_input(saver, plotter)
    conn.listen()

    plotter.plot_detected_objs()
