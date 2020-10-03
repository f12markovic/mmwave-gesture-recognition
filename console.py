#! /usr/bin/env python

import time
import glob
import os
import readline
import binascii
import serial

import matplotlib.pyplot as plt

from cmd import Cmd

from threading import Lock
import queue
from queue import Queue

from mmwave.communication.connection import mmWave
from mmwave.communication.parser import Parser
from mmwave.data.formats import Formats, GESTURE
from mmwave.data.logger import Logger
from mmwave.model.nn import NN
from mmwave.utils.completer import Completer
from mmwave.utils.plotter import Plotter
from mmwave.utils.handlers import SignalHandler
from mmwave.utils.utility_functions import threaded, print, error, warning
from mmwave.utils.flasher import Flasher, CMD, OPCODE

import colorama
from colorama import Fore
colorama.init(autoreset=True)


class Console(Cmd):
    def __init__(self, plotter_queues):
        super().__init__()

        # Connection
        self.cli_port = None
        self.cli_rate = None
        self.data_port = None
        self.data_rate = None

        self.default_cli_rate = 115200
        self.default_data_rate = 921600

        self.firmware_dir = 'firmware/'
        self.flasher = None

        self.mmwave = None
        self.__mmwave_init()
        if self.mmwave is None or self.mmwave.connected is False:
            print('Try connecting manually. Type \'help connect\' for more info.\n')

        # Configuration
        self.config_dir = 'mmwave/communication/profiles/'
        self.configured = False
        self.default_config = 'profile'
        self.config = None

        self.logger = Logger(None)
        self.nn = NN()

        # Catching signals
        self.console_queue = Queue()
        SignalHandler(self.console_queue)

        # Threading stuff
        self.listening_lock = Lock()
        self.printing_lock = Lock()
        self.plotting_lock = Lock()
        self.predicting_lock = Lock()
        self.logging_lock = Lock()

        self.listening = False
        self.printing = False
        self.plotting = False
        self.predicting = False
        self.logging = False

        self.logging_queue = Queue()
        self.data_queue = Queue()
        self.nn_queue = Queue()
        self.plotter_queues = plotter_queues

        self.__set_prompt()
        print('%sInit done.\n' % Fore.GREEN)
        print('%s--- mmWave console ---' % Fore.MAGENTA)
        warning('Type \'help\' for more information.')

    def __mmwave_init(self):
        if self.cli_port is None or self.data_port is None:
            print('Looking for ports...', end='')
            ports = mmWave.find_ports()
            if ports != []:
                self.cli_port = ports[0]
                self.data_port = ports[1]

        self.mmwave = mmWave(self.cli_port, self.data_port,
                             cli_rate=self.default_cli_rate,
                             data_rate=self.default_data_rate)
        if self.mmwave.connected:
            self.flasher = Flasher(self.mmwave)

    def __is_connected(self):
        if self.mmwave is None or not self.mmwave.connected:
            return False
        return True

    def __set_prompt(self):
        if self.__is_connected():
            self.prompt = '%s>>%s ' % (Fore.GREEN, Fore.RESET)
        else:
            self.prompt = '%s[Not connected]%s >> ' % (Fore.RED, Fore.RESET)

    def preloop(self):
        '''
        Initialization before prompting user for commands.
        Despite the claims in the Cmd documentation, Cmd.preloop() is not a
        stub.
        '''
        Cmd.preloop(self)   # sets up command completion
        self._hist = []      # No history yet
        self._locals = {}      # Initialize execution namespace for user
        self._globals = {}

    def postloop(self):
        '''
        Take care of any unfinished business.
        Despite the claims in the Cmd documentation, Cmd.postloop() is not a
        stub.
        '''
        Cmd.postloop(self)   # Clean up command completion
        print('Exiting...')

    def precmd(self, line):
        '''
        This method is called after the line has been input but before
        it has been interpreted. If you want to modify the input line
        before execution (for example, variable substitution) do it here.
        '''
        self._hist += [line.strip()]

        try:
            info = self.plotter_queues['info'].get(False)
            if info == 'closed':
                print('%sPlotter closed.\n' % Fore.YELLOW)
                with self.plotting_lock:
                    if self.plotting:
                        self.plotting = False
        except queue.Empty:
            pass

        return line

    def postcmd(self, stop, line):
        '''
        If you want to stop the console, return something that evaluates to
        true. If you want to do some post command processing, do it here.
        '''
        self.__set_prompt()
        return stop

    def emptyline(self):
        '''Do nothing on empty input line'''
        pass

    def default(self, line):
        '''
        Called on an input line when the command prefix is not recognized.
        In that case we execute the line as Python code.
        '''
        try:
            exec(line) in self._locals, self._globals
        except Exception:
            error('Unknown arguments.')
            return

    def do_help(self, args):
        '''
        Get help on command

        \'help\' or \'?\' with no arguments prints a list of commands for
        which help is available \'help <command>\' or \'? <command>\' gives
        help on <command>
        '''
        # The only reason to define this method is for the help text in
        # the doc string
        Cmd.do_help(self, args)

    def do_history(self, args):
        '''Print a list of commands that have been entered'''
        if args != '':
            error('Unknown arguments.')
            return
        print(self._hist)

    def do_exit(self, args):
        '''Exits from the console'''

        if args != '':
            error('Unknown arguments.')
            return

        self.do_stop()

        if self.__is_connected():
            self.mmwave.disconnect()

        os._exit(0)

    def do_flash(self, args=''):
        '''
        Sending .bin files to mmWave

        Flashing bin files to connected mmWave. It is possible to specify up to
        4 meta files. SOP0 and SOP2 have be closed and power reseted before
        running this command.

        Look \'connect\' and \'autoconnect\' command for connecting to mmWave.

        Usage:
        >> flash xwr16xx_mmw_demo.bin
        '''
        if len(args.split(' ')) > 4:
            error('Too many arguments.')
            return

        if args == '':
            error('Too few arguments.')
            return

        filepaths = []
        for arg in args.split(' '):
            filepath = self.firmware_dir + arg
            if not os.path.isfile(filepath):
                error('File \'%s\' doesn\'t exist.' % filepath)
                return
            filepaths.append(filepath)

        if not self.__is_connected():
            error('Not connected.')
            return

        print('Ping mmWave...', end='')
        response = self.flasher.send_cmd(CMD(OPCODE.PING), resp=False)
        if response is None:
            warning('Check if SOP0 and SOP2 are closed, and reset the power.')
            return
        print('%sDone.' % Fore.GREEN)

        print('Get version...', end='')
        response = self.flasher.send_cmd(CMD(OPCODE.GET_VERSION))
        if response is None:
            return
        print('%sDone.' % Fore.GREEN)
        print('%sVersion:' % Fore.BLUE, binascii.hexlify(response))
        print()

        self.flasher.flash(filepaths, erase=True)
        print('%sDone.' % Fore.GREEN)

    def complete_flash(self, text, line, begidx, endidx):
        completions = []
        for file in glob.glob(self.firmware_dir + '*.bin'):
            completions.append(os.path.basename(file))

        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in completions if s.startswith(mline)]

    def do_autoconnect(self, args=''):
        '''
        Auto connecting to mmWave

        Automatically looking for \'XDS\' ports and connecting with default
        baudrates. Auto-detection is only applicable for eval boards with
        XDS110.

        Look \'connect\' command for manual connection.

        Usage:
        >> autoconnect
        '''
        if args != '':
            error('Unknown arguments.')
            return

        if self.__is_connected():
            warning('Already connected.')
            print('Reconnecting...')

        ports = mmWave.find_ports()
        if ports != []:
            self.cli_port = ports[0]
            self.data_port = ports[1]
            self.__mmwave_init()

    def __get_user_port(self, type):
        old_completer = readline.get_completer()

        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append(port[0])

        compl_ports = Completer(ports)
        readline.set_completer_delims('\t')
        readline.parse_and_bind('tab: complete')
        readline.set_completer(compl_ports.list_completer)

        port = None
        while port is None:
            port = input('%s%s port:%s ' % (Fore.YELLOW, type, Fore.RESET)).strip()
            if port in ['q', 'exit']:
                break
            elif port not in ports:
                error('Port %s is not valid.' % port)
                warning('Valid ports:')
                for port in ports:
                    warning('\t' + port)
                warning('Type \'exit\' to return.')
                port = None

        readline.set_completer(old_completer)
        return port

    def __get_user_rate(self, type, port):
        old_completer = readline.get_completer()

        rates = []
        for rate in mmWave.BAUDRATES:
            rates.append(str(rate))

        compl_rates = Completer(rates)
        readline.set_completer(compl_rates.list_completer)
        rate = None
        while rate is None:
            rate = input('%s%s rate:%s ' % (Fore.YELLOW, type, Fore.RESET)).strip()
            if rate in ['q', 'exit']:
                break
            elif rate == '':
                rate = mmWave.get_baudrate(port)
            elif rate not in rates:
                error('Rate %s is not valid.' % rate)
                warning('Valid baudrates:')
                for rate in rates:
                    warning('\t' + rate)
                warning('Type \'exit\' to return.')
                rate = None
            else:
                rate = int(rate)

        readline.set_completer(old_completer)
        return rate

    def do_connect(self, args=''):
        '''
        Manually connecting to mmWave

        Command will ask you to manualy type ports and baudrates.
        Use <Tab> for autocompletion on available ports and baudrates.
        Type \'exit\' for exiting manual connection.
        If you only press enter on baudrates, console will try to find
        baudrate automatically. Note that this will work only if connection
        is already opened from both sides. (On mmWave startup only cli port
        is open, and data port will open only after \'senstrStart\' command)

        Look \'autoconnect\' command for automatic connection.

        Usage:
        >> connect
        cli port: /dev/ttyACM0
        cli rate: 115200
        data port: /dev/ttyACM1
        data rate: 921600
        '''

        if args != '':
            error('Unknown arguments.')
            return

        if self.__is_connected():
            self.mmwave.disconnect()
            print()

        port = self.__get_user_port('cli')
        if port is not None:
            self.cli_port = port
            self.cli_rate = self.__get_user_rate('cli', port)
        else:
            return

        port = self.__get_user_port('data')
        if port is not None:
            self.data_port = port
            self.data_rate = self.__get_user_rate('data', port)
        else:
            return

        self.__mmwave_init()

    def do_send(self, args=''):
        '''
        Sending configuration to mmWave

        Configuring mmWave with given configuration file. All configuration
        files should be placed in \'mmwave/communication/profiles\' folder.
        Use <Tab> for autocompletion on available configuration files.
        All configuration files should have .cfg extension.
        If no configuration is provided, default configuration file will be
        used.

        Usage:
        >> send
        >> send profile
        '''
        if args == '':
            args = self.default_config

        if len(args.split()) > 1:
            error('Too many arguments.')
            return

        if not self.__is_connected():
            error('Not connected.')
            return

        all_config_files = glob.glob(self.config_dir + '*.cfg')
        for idx, config in enumerate(all_config_files):
            all_config_files[idx] = '/'.join(config.split('\\'))

        cfg = self.config_dir + args + '.cfg'
        if cfg not in all_config_files:
            print('Unknown profile.')
            return

        mmwave_configured = False
        cnt = 0
        while not mmwave_configured and cnt < 5:
            mmwave_configured = self.mmwave.configure(cfg)
            if not mmwave_configured:
                time.sleep(1)
            cnt += 1

        if not mmwave_configured:
            return

        if os.path.basename(cfg) == 'stop.cfg':
            self.configured = False
        else:
            self.configured = True
        self.config = cfg

    def complete_send(self, text, line, begidx, endidx):
        completions = []
        for file in glob.glob(self.config_dir + '*.cfg'):
            completions.append('.'.join(os.path.basename(file).split('.')[:-1]))

        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in completions if s.startswith(mline)]

    @threaded
    def __listen_thread(self):
        print('%s=== Listening ===' % Fore.CYAN)
        while True:
            with self.listening_lock:
                if not self.listening:
                    break

            data = self.mmwave.get_data()

            if data is None:
                time.sleep(3)
                continue

            self.data_queue.put(data)
            time.sleep(0.05)

    @threaded
    def __parse_thread(self):
        parser = Parser(Formats(self.config))

        while True:
            with self.listening_lock:
                if not self.listening:
                    break

            data = self.data_queue.get()
            frame = parser.assemble(data)

            if frame is not None:
                frame = parser.parse(frame, warn=True)
                with self.logging_lock:
                    if self.logging:
                        self.logging_queue.put(frame)

                with self.printing_lock:
                    if self.printing:
                        parser.pprint(frame)

                with self.plotting_lock:
                    if self.plotting:
                        self.plotter_queues['data'].put(frame)

                with self.predicting_lock:
                    if self.predicting:
                        self.nn_queue.put(frame)

            time.sleep(0.05)

    @threaded
    def __predict_thread(self):
        while True:
            with self.predicting_lock:
                if not self.predicting:
                    break

            frame = self.nn_queue.get()

            nn_ready = self.nn.set_sequence(frame)
            if nn_ready:
                self.nn.predict()
                #  self.nn.predict(debug=True)

    @threaded
    def __logging_thread(self):
        while True:
            frame = self.logging_queue.get()
            done = self.logger.log(frame)
            if done:
                break

    def do_listen(self, args=''):
        '''
        Start listener and parser thread

        Starting listener on connected ports. If mmWave is not configured,
        default configuration will be send first.

        Look \'connect\' and \'autoconnect\' command for connecting to mmWave.

        Usage:
        >> listen
        '''
        if args != '':
            error('Unknown arguments.')
            return

        if not self.configured:
            warning('mmWave not configured.')
            warning('Configuring with deafult config...')
            self.do_send(self.default_config)
            if not self.configured:
                error('Configuring failed.')
                return

        with self.listening_lock:
            if self.listening:
                warning('Listener already started.')
                return

        with self.listening_lock:
            self.listening = True

        self.__listen_thread()
        self.__parse_thread()

    def do_stop(self, args=''):
        '''
        Stopping mmwave, listener and plotter.

        Possible options: \'mmwave\', \'listen\' and \'plot\'.
            \'mmwave\': Sending \'sensorStop\' command to mmWave. This option
                        will also stop listener and plotter.
            \'listen\': Stopping listener and parser threads. This option
                        will also stop plotter.
            \'plot\': Closing plotter.
         If nothing is provided as a argument, \'mmwave\' will be used.

        Usage:
        >> stop
        >> stop plot
        '''
        if args == '' or 'mmwave' in args.split():
            opts = ['plot', 'listen', 'mmwave']
        elif 'listen' in args.split():
            opts = ['plot', 'listen']
        else:
            opts = args.split()

        if 'plot' in opts:
            with self.plotting_lock:
                if self.plotting:
                    self.plotting = False
                    print('Plotter stopped.')
            self.plotter_queues['cli'].put('close')
            opts.remove('plot')

        if 'listen' in opts:
            with self.listening_lock:
                if self.listening:
                    self.listening = False
                    print('Listener stopped.')
            opts.remove('listen')

        if 'mmwave' in opts:
            self.do_send('stop')
            print('mmWave stopped.')
            opts.remove('mmwave')

        for opt in opts:
            warning('Unknown option: %s. Skipped.' % opt)

    def complete_stop(self, text, line, begidx, endidx):
        completions = ['mmwave', 'listen', 'plot']

        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in completions if s.startswith(mline)]

    def do_print(self, args=''):
        '''
        Pretty print

        Printing received frames. Listener should be started before using
        this command. Use <Ctrl-C> to stop this command.

        Usage:
        >> print
        '''
        if args != '':
            error('Unknown arguments.')
            return

        with self.listening_lock:
            if not self.listening:
                error('Listener not started.')
                return

        with self.printing_lock:
            self.printing = True

        self.console_queue.get()

        with self.printing_lock:
            self.printing = False

    def do_plot(self, args=''):
        '''
        Start plotter

        Plotting received frames. Listener should be started before using
        this command. Use \'stop plot\' to stop this command.

        Usage:
        >> plot
        '''
        if args != '':
            error('Unknown arguments.')
            return

        with self.listening_lock:
            if not self.listening:
                error('Listener not started.')
                return

        self.plotter_queues['cli'].put('init')

        with self.plotting_lock:
            self.plotting = True

    def do_predict(self, args=''):
        '''
        Start prediction

        Passing received frames through neural network and printing results.
        Listener should be started before using this command.
        Use <Ctrl-C> to stop this command.

        Usage:
        >> predict
        '''
        if args != '':
            error('Unknown arguments.')
            return

        with self.listening_lock:
            if not self.listening:
                error('Listener not started.')
                return

        if not self.nn.weights_loaded:
            self.nn.load_model()
            print()

        with self.predicting_lock:
            self.predicting = True

        self.__predict_thread()

        self.console_queue.get()

        with self.predicting_lock:
            self.predicting = False

    def do_start(self, args=''):
        '''
        Start listener, plotter and prediction.

        If mmWave is not configured, default configuration will be send
        first. Use <Ctrl-C> to stop this command.

        Usage:
        >> start
        '''
        if args != '':
            error('Unknown arguments.')
            return

        if not self.nn.weights_loaded:
            self.nn.load_model()
            print()

        self.do_send(self.default_config)
        self.do_listen()
        self.do_plot()
        self.do_predict()
        self.do_stop()

    def do_train(self, args=''):
        '''
        Train neural network

        Command will first load cached X and y data located in
        'mmwave/data/.X_data' and 'mmwave/data/.y_data' files. This data will be
        used for the training process. If you want to read raw .csv files,
        provide \'refresh\' (this will take few minutes).

        Usage:
        >> train
        >> train refresh
        '''

        if len(args.split()) > 1:
            error('Unknown arguments.')
            return

        if args == '':
            self.nn.train()
        elif args == 'refresh':
            self.nn.train(refresh_data=True)
        else:
            warning('Unknown argument: %s' % args)

    def complete_train(self, text, line, begidx, endidx):
        completions = ['refresh']

        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in completions if s.startswith(mline)]

    def do_eval(self, args=''):
        '''
        Evaluate neural network

        Command will first load cached X and y data located in
        'mmwave/data/.X_data' and 'mmwave/data/.y_data' files. This data will be
        used for the evaluating process. If you want to read raw .csv files,
        provide \'refresh\' (this will take few minutes).

        Usage:
        >> eval
        >> eval refresh
        '''

        if len(args.split()) > 1:
            error('Unknown arguments.')
            return

        if args == '':
            self.nn.evaluate()
        elif args == 'refresh':
            self.nn.evaluate(refresh_data=True)
        else:
            warning('Unknown argument: %s' % args)

    def complete_eval(self, text, line, begidx, endidx):
        completions = ['refresh']

        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in completions if s.startswith(mline)]

    def do_log(self, args=''):
        '''
        Log data

        Logging specified gesture. Data will be saved in
        \'mmwave/data/gesture_foder/sameple_num.csv\' file.
        Possible options: \'up\', \'down\', \'left\', \'right\', \'cw\',
                          \'ccw\', \'s\', \'z\', \'x\'

        Usage:
        >> log up
        >> log ccw
        >> log z
        '''
        if args == '':
            error('too few arguments.')
            return

        if len(args.split()) > 1:
            error('Unknown arguments.')
            return

        with self.listening_lock:
            if not self.listening:
                error('Listener not started.')
                return

        if args == 'up':
            gesture = GESTURE.SWIPE_UP
        elif args == 'down':
            gesture = GESTURE.SWIPE_DOWN
        elif args == 'right':
            gesture = GESTURE.SWIPE_RIGHT
        elif args == 'left':
            gesture = GESTURE.SWIPE_LEFT
        elif args == 'cw':
            gesture = GESTURE.SPIN_CW
        elif args == 'ccw':
            gesture = GESTURE.SPIN_CCW
        elif args == 'z':
            gesture = GESTURE.LETTER_Z
        elif args == 'x':
            gesture = GESTURE.LETTER_X
        elif args == 's':
            gesture = GESTURE.LETTER_S
        else:
            warning('Unknown argument: %s' % args)
            return

        self.logger.set_gesture(gesture)

        with self.logging_lock:
            self.logging = True

        self.__logging_thread().join()

        with self.logging_lock:
            self.logging = False

    def complete_log(self, text, line, begidx, endidx):
        completions = ['up', 'down', 'left', 'right', 'cw', 'ccw', 's', 'x', 'z']

        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in completions if s.startswith(mline)]

    def do_remove(self, args=''):
        '''
        Remove last sample

        Removing last gesture sample. Data will be removed from
        \'mmwave/data/gesture_foder\' folder.
        Possible options: \'up\', \'down\', \'left\', \'right\', \'cw\',
                          \'ccw\', \'s\', \'z\', \'x\'
        Usage:
        >> remove up
        >> remove ccw
        >> remove z
        '''
        if args == '':
            error('too few arguments.')
            return

        if len(args.split()) > 1:
            error('Unknown arguments.')
            return

        if args == 'up':
            gesture = GESTURE.SWIPE_UP
        elif args == 'down':
            gesture = GESTURE.SWIPE_DOWN
        elif args == 'right':
            gesture = GESTURE.SWIPE_RIGHT
        elif args == 'left':
            gesture = GESTURE.SWIPE_LEFT
        elif args == 'cw':
            gesture = GESTURE.SPIN_CW
        elif args == 'ccw':
            gesture = GESTURE.SPIN_CCW
        elif args == 'z':
            gesture = GESTURE.LETTER_Z
        elif args == 'x':
            gesture = GESTURE.LETTER_X
        elif args == 's':
            gesture = GESTURE.LETTER_S
        else:
            warning('Unknown argument: %s' % args)
            return

        self.logger.set_gesture(gesture)
        self.logger.discard_last_sample()

    def complete_remove(self, text, line, begidx, endidx):
        completions = ['up', 'down', 'left', 'right', 'cw', 'ccw', 's', 'x', 'z']

        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in completions if s.startswith(mline)]

    def do_redraw(self, args=''):
        '''
        Redraw sample

        Redrawing last captured gesture file.
        Possible options: \'up\', \'down\', \'left\', \'right\', \'cw\',
                          \'ccw\', \'s\', \'z\', \'x\'

        Usage:
        >> redraw up
        >> redraw ccw
        >> redraw z
        '''
        if args == '':
            error('too few arguments.')
            return

        if len(args.split()) > 1:
            error('Unknown arguments.')
            return

        with self.listening_lock:
            if not self.listening:
                error('Listener not started.')
                return

        with self.plotting_lock:
            if not self.plotting:
                error('Plotter not started.')
                return

        if args == 'up':
            gesture = GESTURE.SWIPE_UP
        elif args == 'down':
            gesture = GESTURE.SWIPE_DOWN
        elif args == 'right':
            gesture = GESTURE.SWIPE_RIGHT
        elif args == 'left':
            gesture = GESTURE.SWIPE_LEFT
        elif args == 'cw':
            gesture = GESTURE.SPIN_CW
        elif args == 'ccw':
            gesture = GESTURE.SPIN_CCW
        elif args == 'z':
            gesture = GESTURE.LETTER_Z
        elif args == 'x':
            gesture = GESTURE.LETTER_X
        elif args == 's':
            gesture = GESTURE.LETTER_S
        else:
            warning('Unknown argument: %s' % args)
            return

        self.plotter_queues['cli'].put('redraw')
        self.plotter_queues['cli'].put(gesture)

    def complete_redraw(self, text, line, begidx, endidx):
        completions = ['up', 'down', 'left', 'right', 'cw', 'ccw', 's', 'x', 'z']

        mline = line.partition(' ')[2]
        offs = len(mline) - len(text)
        return [s[offs:] for s in completions if s.startswith(mline)]


@threaded
def console_thread(console):
    while True:
        console.cmdloop()


def init_plotter(plotter_queues):
    while True:
        try:
            cmd = plotter_queues['cli'].get(False)
            if cmd == 'init':
                plt.close('all')
                plotter = Plotter(plotter_queues['info'])
                plotter.show()
                plt.gcf().canvas.flush_events()
                return plotter
        except queue.Empty:
            pass
        time.sleep(0.05)


def set_plotter(plotter, command):
    try:
        cmd = command.get(False)
        if cmd == 'close':
            if plotter is not None:
                plotter.close()
            return None
        elif cmd == 'redraw':
            gesture = command.get()
            if plotter is not None:
                plotter.draw_last_sample(gesture)
    except queue.Empty:
        pass
    return plotter


def plotting(plotter_queues):
    plotter = None
    while True:
        if plotter is None:
            plotter = init_plotter(plotter_queues)
        else:
            plotter = set_plotter(plotter, plotter_queues['cli'])

        # Plot data
        if plotter is not None:
            try:
                frame = plotter_queues['data'].get(False)
                plt.gcf().canvas.flush_events()
                plotter.plot_detected_objs(frame)
            except queue.Empty:
                pass

        time.sleep(0.05)


if __name__ == '__main__':
    plotter_queues = {'data': Queue(), 'cli': Queue(), 'info': Queue()}
    console_thread(Console(plotter_queues))

    # Plotter has to be located in the main thread
    plotting(plotter_queues)
