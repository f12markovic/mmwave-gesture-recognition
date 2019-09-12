#! /usr/bin/env python

import os
import time
from queue import Queue

import serial
import serial.tools.list_ports

from constants import MAGIC_NUM
from utility_functions import threaded, print


class Connection:
    def __init__(self, cfgPort, dataPort):
        self.__cfgPort = serial.Serial(port=cfgPort,
                                       baudrate=115200,
                                       timeout=2,
                                       stopbits=serial.STOPBITS_ONE,
                                       bytesize=serial.EIGHTBITS)

        self.__dataPort = serial.Serial(port=dataPort,
                                        baudrate=921600,
                                        timeout=2,
                                        stopbits=serial.STOPBITS_ONE,
                                        bytesize=serial.EIGHTBITS)

        self.__dataQueue = Queue()

        self.__sync = False
        self.__frame = ''
        self.__last_frame_num = 0
        self.__connection_time = 0

    def __sendFrame(self, data):
        magic_idx = data.find(MAGIC_NUM)
        if self.__sync is True:
            if magic_idx >= 0:
                # End of frame
                self.__frame = self.__frame + ':' + data[:magic_idx-1]
                # Send to queue
                self.__dataQueue.put(self.__frame)
                # Start new frame from here
                self.__frame = data[magic_idx:]
            else:
                # Wait for rest of the frame
                self.__frame = self.__frame + ':' + data
        else:
            if magic_idx >= 0:
                # Put in buffer and wait end of the frame
                self.__frame = data[magic_idx:]
                self.__sync = True
                print('Sync received!\n')
            else:
                print('Waiting for sync...')

    def __resetConnection(self):
        self.__cfgPort.close()
        self.__dataPort.close()
        print()
        print('Data not received, reseting connection...')
        self.__cfgPort.open()
        self.__dataPort.open()

    def sendCfg(self, profile):
        print('Configuring mmWave...')
        if os.path.isfile(profile):
            with open(profile, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    self.__cfgPort.write(line.encode())
                    print('Sending command: ' + line, end='')

                    # Wait for responses
                    self.__connection_time = time.time()
                    response_rec = False
                    while True:
                        if self.__cfgPort.in_waiting > 0:
                            data = self.__cfgPort.readline()
                            try:
                                data = data.decode()
                            except UnicodeDecodeError:
                                self.__resetConnection()
                                time.sleep(1)
                                return False

                            if response_rec is True:
                                if data == 'Done\n':
                                    print('Done\n')
                                    response_rec = False
                                    time.sleep(0.001)
                                    break
                            else:
                                if (data == '\rmmwDemo:/>' + line
                                        or 'Debug' in data
                                        or data == line):
                                    response_rec = True
                                else:
                                    print('Sending failed:')
                                    print(data)
                                    self.__resetConnection()
                                    time.sleep(1)
                                    return False

                        if time.time() - self.__connection_time > 2:
                            self.__resetConnection()
                            self.__connection_time = time.time()
                            return False
                return True

        else:
            print('Profile not found.')
            return False

    def getFrame(self):
        return self.__dataQueue.get()

    def readDone(self):
        self.__dataQueue.task_done()

    @threaded
    def listen(self):
        print('Serial listener started.')
        while True:
            if self.__dataPort.in_waiting > 0:
                serial_string = self.__dataPort.readline()
                data = ':'.join('{:02x}'.format(x) for x in serial_string)
                self.__sendFrame(data)

    @staticmethod
    def findPorts():
        ports = []
        for port in serial.tools.list_ports.comports():
            if 'XDS110' in str(port):
                ports.append(str(port).split(' ')[0])

        if len(ports) != 2:
            print('Ports not found!')
            time.sleep(5)
            return []

        ports.sort()
        return ports
