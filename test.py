#! /usr/bin/env python

import time

from parser import Parser
from nn import NN
from plotter import Plotter
from connection import Connection
from utility_functions import threaded


@threaded
def nn_thread(p):
    nn = NN(p)
    nn.load_model()
    print()
    while True:
        collected = False
        while not collected:
            collected = nn.get_data()
            time.sleep(0.05)
        nn.predict(debug=True)
        time.sleep(0.05)


@threaded
def interpretor(c, p):
    while True:
        frame = c.getFrame()
        p.parse(frame)
        c.readDone()
        time.sleep(0.05)


if __name__ == '__main__':
    ports = []
    while ports == []:
        ports = Connection.findPorts()
    conn = Connection(ports[0], ports[1])

    mmwave_configured = False
    while not mmwave_configured:
        mmwave_configured = conn.sendCfg('./profiles/profile.cfg')

    parser = Parser()
    plotter = Plotter(parser)

    interpretor(conn, parser)
    nn_thread(parser)
    conn.listen()

    plotter.plot_detected_objs()
