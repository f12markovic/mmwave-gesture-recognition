#! /usr/bin/env python

import re
import time

import serial
import serial.tools.list_ports

import colorama
from colorama import Fore
colorama.init(autoreset=True)


class Connection:
    TIMEOUT = 1
    BAUDRATES = [
        9600,
        38400,
        19200,
        57600,
        115200,
        921600
    ]

    def __init__(self, cli_port, data_port,
                       cli_rate=None, data_rate=None):
        self.cached_args = None
        self.connected = False

        self.data_port = data_port
        self.cli_port = cli_port

        self.__connect(cli_port, data_port, cli_rate, data_rate)

    def __connect(self, cli_port, data_port, cli_rate=None, data_rate=None):
        if self.connected:
            self.disconnect()

        # Save args
        self.cached_args = locals()

        # Arg check
        for rate in [cli_rate, data_rate]:
            if rate is not None and rate not in self.BAUDRATES:
                print('%sBaudate not valid.' % Fore.RED)
                self.__update_status()
                return None

        # Data port
        self.data_port = self.__connect_port(data_port, data_rate)

        # Cli port
        if cli_port in [None, data_port]:
            self.cli_port = self.data_port
        else:
            self.cli_port = self.__connect_port(cli_port, cli_rate)
        self.__update_status()
    connect = __connect

    def __connect_port(self, port, rate=None):
        if port is None:
            return

        print('Connecting to port %s\'%s\'' % (Fore.BLUE, port))
        try:
            conn = serial.Serial(port,
                                 bytesize=serial.EIGHTBITS,
                                 parity=serial.PARITY_NONE,
                                 stopbits=serial.STOPBITS_ONE,
                                 xonxoff=False,
                                 rtscts=False,
                                 dsrdtr=False,
                                 writeTimeout=0,
                                 timeout=self.TIMEOUT)

        except serial.serialutil.SerialException:
            print('%sPort \'%s\' not available. Check your connection and permissions'
                    % (Fore.RED, port))
            print('%sAvailable ports:' % Fore.YELLOW)
            for port in serial.tools.list_ports.comports():
                print('\t%s%s' % (Fore.YELLOW, port))
            self.data_port = self.cli_port = None
            self.__update_status(echo=True)
            return

        if rate is None:
            rate = self.get_baudrate(port)

        if rate is None:
            conn.close()
            return

        print('Selecting baud rate %s%d' % (Fore.BLUE, rate))
        conn.baudrate = rate

        return conn

    def __update_status(self, echo=False):
        if None in [self.data_port, self.cli_port]:
            self.data_port, self.cli_port = None, None
            self.connected = False
            if echo:
                print('%sNot connected.\n' % Fore.RED)
        else:
            self.connected = True
            if echo:
                print('%sConnected.\n' % Fore.GREEN)

    @classmethod
    def from_config(cls, config):
        data_port, data_rate = config['data_portname'], config['data_baudrate']
        cli_port, cli_rate = config['cli_portname'], config['cli_baudrate']

        return cls(data_port=data_port, data_rate=data_rate,
                   cli_port=cli_port, cli_rate=cli_rate)

    def reset(self):
        self.close()

        self.data_port.open()
        if self.data_port is not self.cli_port:
            self.cli_port.open()

    def __close(self):
        if self.data_port is not None:
            self.data_port.close()
        if self.data_port is not self.cli_port:
            if self.cli_port is not None:
                self.cli_port.close()
    close = __close

    def disconnect(self):
        print('Disconnecting...', end='')
        self.__close()
        time.sleep(1)

        self.data_port, self.data_port = None, None
        self.__update_status()

    def __reconnect(self):
        if not self.connected:
            print('%smmWave not connected. Reconnecting...' % Fore.RED, end='')
            self.__connect(self.cached_args['data_port'],
                           self.cached_args['data_rate'],
                           self.cached_args['cli_port'],
                           self.cached_args['cli_rate'])

            if not self.connected:
                print('%sCan\'t connect mmWave. Aborting.' % Fore.RED)
                return False

        return True
    reconnect = __reconnect

    def set_cli_baudrate(self, rate):
        self.cli_port.baudrate = rate

    def set_data_baudrate(self, rate):
        self.data_port.baudrate = rate

    def send_cmd(self, data, encoding=None, size=None):
        if not self.__reconnect():
            return None

        try:
            if encoding is not None:
                self.cli_port.write(bytes(data, encoding=encoding))
            else:
                self.cli_port.write(bytes(data))

            if size is not None:
                response = self.cli_port.read(size)
                return response
            else:
                self.cli_port.readline()
                return self.cli_port.readline()
        except serial.serialutil.SerialException:
            print('%sCan\'t write/read from port. Please check your connection or permissions.'
                  % Fore.RED)
            return None

    def get_data(self):
        if not self.__reconnect():
            return None

        try:
            data = self.data_port.read(self.data_port.in_waiting)
        except OSError:
            self.data_port, self.cli_port = None, None
            self.__update_status()
            return None

        return data

    def get_cmd(self, size=None):
        if not self.__reconnect():
            return None

        try:
            if size is None:
                data = self.cli_port.read(self.data_port.in_waiting)
            else:
                data = self.cli_port.read(size)
        except OSError:
            self.data_port, self.cli_port = None, None
            self.__update_status()
            return None

        return data

    @staticmethod
    def get_baudrate(port):
        print('Automatic baud rate search...', end='', flush=True)
        test_packet = 'qWeRtYuIoPaSdFgHjKLzXcVbNm\n'

        try:
            test_conn = serial.Serial(port, timeout=Connection.TIMEOUT,
                                            write_timeout=Connection.TIMEOUT)
        except serial.serialutil.SerialException:
            print('%sCan\'t write to port. Please check your connection or permissions.'
                  % Fore.RED)
            return None

        detected_baudrate = None
        for baudrate in reversed(Connection.BAUDRATES):
            test_conn.baudrate = baudrate

            start_time = time.time()
            while time.time() - start_time < Connection.TIMEOUT:
                try:
                    test_conn.write(bytes(test_packet, encoding='ascii'))
                except serial.serialutil.SerialTimeoutException:
                    print('%sCan\'t write to port. Please check your connection or permissions.'
                          % Fore.RED)
                    return None

                time.sleep(0.01)
                response = test_conn.read(test_conn.in_waiting)

                if bytes(test_packet, encoding='ascii') in response:
                    detected_baudrate = baudrate
                    break

            if detected_baudrate is not None:
                print('Detected baud rate %s%d.' % (Fore.BLUE, detected_baudrate))
                break
        else:
            print()
            print(Fore.YELLOW +
                  'Is the connection open? If not, baudrate should be specified manually.')
            print(Fore.RED +
                  'No valid baud rate detected. Please check your connection.')

        test_conn.close()
        return detected_baudrate


class mmWave(Connection):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config_file = None

    def configure(self, config_file):
        self.config_file = config_file

        with open(config_file, 'r') as f:
            lines = f.readlines()

        print('Configuring mmWave:')
        for line in lines:
            # Skip comment lines and blank lines
            if re.match('(^\s*%|^\s*$)', line):
                continue

            # Send cmd
            print('Sending:  %s%s' % (Fore.YELLOW, line), end='')
            response = self.send_cmd(line, encoding='ascii')
            if response is None:
                return False

            # Parse response
            response = response.decode('ascii', errors='ignore')
            if 'Done' not in response and 'sensorStart' not in line:
                print('Received: %s%s' % (Fore.RED, response))
                print('%sFailed sending configuration' % Fore.RED)
                self.reset()
                return False
            else:
                print('Received: %s%s' % (Fore.GREEN, response))

            if 'sensorStart' not in line:
                time.sleep(0.01)

        return True

    @staticmethod
    def find_ports():
        ports = []
        for port in serial.tools.list_ports.comports():
            if 'XDS110' in str(port):
                ports.append(str(port).split(' ')[0])

        if len(ports) < 2:
            print('%sPorts not found!' % Fore.RED)
            print('%sAuto-detection is only applicable for eval boards with XDS110.'
                    % Fore.YELLOW)
            return []

        ports.sort()
        return ports
