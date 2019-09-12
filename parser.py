#! /usr/bin/env python

from threading import Lock

from utility_functions import splitter, print, warning
from constants import MAGIC_NUM, VERSION, PLATFORM, STRUCT_TAG


class Parser:
    def __init__(self, warn=False):
        self.__warn = warn

        self.__struct = {}
        self.__frame = {}

        self.__det_objs_struct = {}
        self.__stats_struct = {}

        self.__head = 0
        self.__tail = 0
        self.__saved_head = 0
        self.__saved_tail = 0

        self.__previous_frame_num = 0
        self.__valid_frame = False

        self.__lock = Lock()

    def __reset_frame(self):
        self.__frame = {
            'header': {
                'magic_number': '',
                'version': '',
                'packet_len': 0,
                'platform': '',
                'frame_num': 0,
                'cpu_cycles': 0,
                'num_of_det_objs': 0,
                'num_of_structs': 0,
                'current_subframe': 0
            },
            'struct': []
        }

        self.__struct = {
            'tag': 0,
            'len': 0,
            'payload': ''
        }

        self.__det_objs_struct = {
            'descriptor': {
                'num_of_det_objs': 0,
                'xyz_q_format': 0
            },
            'obj': []
        }

        self.__stats_struct = {
            'inter_frame_proc_time': 0,
            'trans_out_time': 0,
            'inter_frame_proc_margin': 0,
            'inter_chirp_proc_margin': 0,
            'active_frame_cpu_load': 0,
            'inter_frame_cpu_load': 0
        }

        self.__head = 0
        self.__tail = 0
        self.__valid_frame = False

    def __save_head_tail(self):
        self.__saved_head = self.__head
        self.__saved_tail = self.__tail
        self.__head = 0
        self.__tail = 0

    def __restore_head_tail(self):
        self.__head = self.__saved_head
        self.__tail = self.__saved_tail

    def __inc_idx(self, length):
        self.__head = self.__tail
        self.__tail = self.__head + length

    def __parse_header(self, frame):
        self.__inc_idx(8)
        self.__frame['header']['magic_num'] = (
            ':'.join(frame[self.__head:self.__tail])
        )
        if self.__frame['header']['magic_num'] != MAGIC_NUM:
            if self.__warn:
                warning('Sync number not correct.',
                        self.__frame['header']['magic_num'], MAGIC_NUM)
            self.__valid_frame = False
            return

        self.__inc_idx(4)
        self.__frame['header']['version'] = (
            '.'.join(frame[self.__head:self.__tail][::-1])
        )
        if self.__frame['header']['version'] != VERSION:
            if self.__warn:
                warning('Version number not correct.',
                        self.__frame['header']['version'], VERSION)
            self.__valid_frame = False
            return

        self.__inc_idx(4)
        self.__frame['header']['packet_len'] = (
            int(''.join(frame[self.__head:self.__tail][::-1]), 16)
        )
        if self.__frame['header']['packet_len'] != len(frame):
            if self.__warn:
                warning('Packet size not correct.',
                        str(len(frame)),
                        str(self.__frame['header']['packet_len']))
            self.__valid_frame = False
            return

        self.__inc_idx(4)
        self.__frame['header']['platform'] = (
            (''.join(frame[self.__head:self.__tail][::-1])).lstrip('0')
        )
        if self.__frame['header']['platform'] != PLATFORM:
            if self.__warn:
                warning('Platform type not correct.',
                        self.__frame['header']['platform'], PLATFORM)
            self.__valid_frame = False
            return

        self.__inc_idx(4)
        self.__frame['header']['frame_num'] = (
            int(''.join(frame[self.__head:self.__tail][::-1]), 16)
        )
        lost_frames = (self.__frame['header']['frame_num']
                       - self.__previous_frame_num - 1)
        if lost_frames < 0:
            if self.__warn:
                warning('Negative number of lost frames received.',
                        str(lost_frames), '>0')
            self.__valid_frame = False
            return

        if self.__warn:
            if lost_frames == 1:
                print('1 frame lost.')
                print()
            elif lost_frames > 1:
                print(str(lost_frames) + ' frames lost.')
                print()

        self.__previous_frame_num = self.__frame['header']['frame_num']

        self.__inc_idx(4)
        self.__frame['header']['cpu_cycles'] = (
            int(''.join(frame[self.__head:self.__tail][::-1]), 16)
        )

        self.__inc_idx(4)
        self.__frame['header']['num_of_det_objs'] = (
            int(''.join(frame[self.__head:self.__tail][::-1]), 16)
        )

        self.__inc_idx(4)
        self.__frame['header']['num_of_structs'] = (
            int(''.join(frame[self.__head:self.__tail][::-1]), 16)
        )

        self.__inc_idx(4)
        self.__frame['header']['current_subframe'] = (
            int(''.join(frame[self.__head:self.__tail][::-1]), 16)
        )

        self.__valid_frame = True

    def __parse_struct(self, frame):
        self.__inc_idx(4)
        self.__struct['tag'] = (
            int(''.join(frame[self.__head:self.__tail][::-1]), 16)
        )
        if self.__struct['tag'] > 6 or self.__struct['tag'] == 0:
            if self.__warn:
                print('Invalid tag \'' + str(self.__struct['tag']) + '\'.')
                print('Frame dropped.')
            self.__valid_frame = False
            return

        self.__inc_idx(4)
        self.__struct['len'] = (
            int(''.join(frame[self.__head:self.__tail][::-1]), 16)
        )
        if self.__struct['len'] > len(frame[self.__tail:]):
            self.__valid_frame = False
            if self.__warn:
                print('Invalid size of struct.', end='')
                print('Received \'' + str(self.__struct['len']) + '\', ', end='')
                print('left size in struct \'' + len(frame[self.__tail:]) + '\'.')
                print('Frame dropped.')
            return

        self.__inc_idx(self.__struct['len'])
        self.__struct['payload'] = (
            ':'.join(frame[self.__head:self.__tail])
        )

        self.__frame['struct'].append(self.__struct.copy())

        if self.__struct['tag'] == STRUCT_TAG.DETECTED_POINTS:
            self.__parse_detected_points()
        elif self.__struct['tag'] == STRUCT_TAG.RANGE_PROFILE:
            self.__parse_range_profile()
        elif self.__struct['tag'] == STRUCT_TAG.NOISE_PROFILE:
            self.__parse_noise_profile()
        elif self.__struct['tag'] == STRUCT_TAG.RANGE_AZIMUTH_HEAT_MAP:
            self.__parse_azimuth_heat_map()
        elif self.__struct['tag'] == STRUCT_TAG.RANGE_DOPPLER_HEAT_MAP:
            self.__parse_doppler_heat_map()
        elif self.__struct['tag'] == STRUCT_TAG.STATS:
            self.__parse_statistics()

    def __parse_detected_points(self):
        self.__save_head_tail()
        payload = self.__struct['payload'].split(':')

        self.__inc_idx(2)
        self.__det_objs_struct['descriptor']['num_of_det_objs'] = (
            int(''.join(payload[self.__head:self.__tail][::-1]), 16)
        )

        self.__inc_idx(2)
        self.__det_objs_struct['descriptor']['xyz_q_format'] = (
            int(''.join(payload[self.__head:self.__tail][::-1]), 16)
        )
        if (self.__frame['header']['num_of_det_objs'] !=
                self.__det_objs_struct['descriptor']['num_of_det_objs']):
            if self.__warn:
                warning('Invalid number of detected objets.',
                        self.__frame['header']['num_of_det_objs'],
                        self.__det_objs_struct['descriptor']['num_of_det_objs'])
            self.__valid_frame = False
            return

        for _ in range(self.__det_objs_struct['descriptor']['num_of_det_objs']):
            obj = {}

            self.__inc_idx(2)
            obj['range_idx'] = (
                int(''.join(payload[self.__head:self.__tail][::-1]), 16)
            )

            self.__inc_idx(2)
            obj['doppler_idx'] = (
                int(''.join(payload[self.__head:self.__tail][::-1]), 16)
            )

            self.__inc_idx(2)
            obj['peak_value'] = (
                int(''.join(payload[self.__head:self.__tail][::-1]), 16)
            )

            self.__inc_idx(2)
            obj['x_coord'] = (
                int(''.join(payload[self.__head:self.__tail][::-1]), 16)
            )

            self.__inc_idx(2)
            obj['y_coord'] = (
                int(''.join(payload[self.__head:self.__tail][::-1]), 16)
            )

            self.__inc_idx(2)
            obj['z_coord'] = (
                int(''.join(payload[self.__head:self.__tail][::-1]), 16)
            )

            self.__det_objs_struct['obj'].append(obj.copy())

        self.__restore_head_tail()

    def __parse_range_profile(self):
        pass

    def __parse_noise_profile(self):
        pass

    def __parse_azimuth_heat_map(self):
        pass

    def __parse_doppler_heat_map(self):
        pass

    def __parse_statistics(self):
        self.__save_head_tail()
        payload = self.__struct['payload'].split(':')

        self.__inc_idx(4)
        self.__stats_struct['inter_frame_proc_time'] = (
            int(''.join(payload[self.__head:self.__tail][::-1]), 16)
        )

        self.__inc_idx(4)
        self.__stats_struct['trans_out_time'] = (
            int(''.join(payload[self.__head:self.__tail][::-1]), 16)
        )

        self.__inc_idx(4)
        self.__stats_struct['inter_frame_proc_margin'] = (
            int(''.join(payload[self.__head:self.__tail][::-1]), 16)
        )

        self.__inc_idx(4)
        self.__stats_struct['inter_chirp_proc_margin'] = (
            int(''.join(payload[self.__head:self.__tail][::-1]), 16)
        )

        self.__inc_idx(4)
        self.__stats_struct['active_frame_cpu_load'] = (
            int(''.join(payload[self.__head:self.__tail][::-1]), 16)
        )

        self.__inc_idx(4)
        self.__stats_struct['inter_frame_cpu_load'] = (
            int(''.join(payload[self.__head:self.__tail][::-1]), 16)
        )

        self.__restore_head_tail()

    def parse(self, frame):
        self.lock_data()
        try:
            self.__reset_frame()
            frame = frame.split(':')
            self.__parse_header(frame)

            for _ in range(self.__frame['header']['num_of_structs']):
                if self.__valid_frame:
                    self.__parse_struct(frame)

            # Check padding frames
            if self.__valid_frame:
                if self.__tail > len(frame):
                    if (len(frame[self.__tail:]) > 31 or not
                            (frame[self.__tail:] == frame[self.__tail:] and
                             frame[self.__tail].upper() == '0F')):
                        if self.__warn:
                            print('Padding not correct.')
                            print('Frame dropped.')
                            print()
                        self.__valid_frame = False
        finally:
            self.unlock_data()

    def __print_header(self):
        print('Frame: ')
        print('|\tHeader:')

        print('|\t|\tMagic num:                  ', end='')
        print(self.__frame['header']['magic_num'])

        print('|\t|\tVersion:                    ', end='')
        print(self.__frame['header']['version'])

        print('|\t|\tTotal packet length:        ', end='')
        print(str(self.__frame['header']['packet_len']) + ' bytes')

        print('|\t|\tPlatform:                   ', end='')
        print(self.__frame['header']['platform'])

        print('|\t|\tFrame number:               ', end='')
        print(str(self.__frame['header']['frame_num']))

        print('|\t|\tCPU cycles:                 ', end='')
        print(str(self.__frame['header']['cpu_cycles']))

        print('|\t|\tNumber of detected objects: ', end='')
        print(str(self.__frame['header']['num_of_det_objs']))

        print('|\t|\tNumber of structures:       ', end='')
        print(str(self.__frame['header']['num_of_structs']))

        print('|\t|\tCurrent subframe:           ', end='')
        print(str(self.__frame['header']['current_subframe']))

        print('|')

    def __print_detected_points(self, s):
        print('|\t|\tDetected Objects')
        print('|\t|\t|\tLength: ' + str(s['len']) + ' bytes')
        for o_idx, obj in enumerate(self.__det_objs_struct['obj']):
            print('|\t|\t|\tObject: ' + str(o_idx + 1))
            print('|\t|\t|\t|\tRange index:     ', obj['range_idx'])
            print('|\t|\t|\t|\tDoppler index:   ', obj['doppler_idx'])
            print('|\t|\t|\t|\tPeak value:      ', obj['peak_value'])
            print('|\t|\t|\t|\tX coordinate:    ', obj['x_coord'])
            print('|\t|\t|\t|\tY coordinate:    ', obj['y_coord'])
            print('|\t|\t|\t|\tZ coordinate:    ', obj['z_coord'])

            if o_idx != len(self.__det_objs_struct['obj']) - 1:
                print('|\t|\t|')

    def __print_range_profile(self, s):
        print('|\t|\tRange Profile')
        print('|\t|\t|\tLength:    ' + str(s['len']) + ' bytes')
        print('|\t|\t|\tPayload:   ', end='')
        appender = ''
        for piece in splitter(16, s['payload']):
            print(appender + piece)
            appender = '|\t|\t|\t|          '

    def __print_azimuth_heat_map(self, s):
        print('|\t|\tRange Azimuth Head Map')
        print('|\t|\t|\tLength:    ' + s['len'] + ' bytes')
        print('|\t|\t|\tPayload:   ', end='')
        appender = ''
        for piece in splitter(16, s['payload']):
            print(appender + piece)
            appender = '|\t|\t|\t|          '

    def __print_noise_profile(self, s):
        print('|\t|\tNoise Profile')
        print('|\t|\t|\tLength:    ' + s['len'] + ' bytes')
        print('|\t|\t|\tPayload:   ', end='')
        appender = ''
        for piece in splitter(16, s['payload']):
            print(appender + piece)
            appender = '|\t|\t|\t|          '

    def __print_doppler_heat_map(self, s):
        print('|\t|\tRange Doppler Heat Map')
        print('|\t|\t|\tLength:    ' + s['len'] + ' bytes')
        print('|\t|\t|\tPayload:   ', end='')
        appender = ''
        for piece in splitter(16, s['payload']):
            print(appender + piece)
            appender = '|\t|\t|\t|          '

    def __print_statistics(self, s):
        print('|\t|\tStatistics')
        print('|\t|\t|\tLength: ' + str(s['len']) + ' bytes')
        print('|\t|\t|\tPayload:')
        print('|\t|\t|\t|\tInter-frame Processing Time:   ', end='')
        print(self.__stats_struct['inter_frame_proc_time'])
        print('|\t|\t|\t|\tTransmit Output Time:          ', end='')
        print(self.__stats_struct['trans_out_time'])
        print('|\t|\t|\t|\tInter-frame Processing Margin: ', end='')
        print(self.__stats_struct['inter_frame_proc_margin'])
        print('|\t|\t|\t|\tInter-chirp Processing Margin: ', end='')
        print(self.__stats_struct['inter_chirp_proc_margin'])
        print('|\t|\t|\t|\tActive Frame CPU Load:         ', end='')
        print(self.__stats_struct['active_frame_cpu_load'])
        print('|\t|\t|\t|\tInter-frame CPU Load:          ', end='')
        print(self.__stats_struct['inter_frame_cpu_load'])

    def __print_structs(self):
        for s_idx, s in enumerate(self.__frame['struct']):
            if s_idx == 0:
                print('|\tStructure')

            if s['tag'] == STRUCT_TAG.DETECTED_POINTS:
                self.__print_detected_points(s)
                if s_idx != self.__frame['header']['num_of_structs'] - 1:
                    print('|\t|')

            elif s['tag'] == STRUCT_TAG.RANGE_PROFILE:
                self.__print_range_profile(s)
                if s_idx != self.__frame['header']['num_of_structs']-1:
                    print('|\t|')

            elif s['tag'] == STRUCT_TAG.NOISE_PROFILE:
                self.__print_noise_profile(s)
                if s_idx != self.__frame['header']['num_of_structs']-1:
                    print('|\t|')

            elif s['tag'] == STRUCT_TAG.RANGE_AZIMUTH_HEAT_MAP:
                self.__print_azimuth_heat_map(s)
                if s_idx != self.__frame['header']['num_of_structs']-1:
                    print('|\t|')

            elif s['tag'] == STRUCT_TAG.RANGE_DOPPLER_HEAT_MAP:
                self.__print_doppler_heat_map(s)
                if s_idx != self.__frame['header']['num_of_structs']-1:
                    print('|\t|')

            elif s['tag'] == STRUCT_TAG.STATS:
                self.__print_statistics(s)
                if s_idx != self.__frame['header']['num_of_structs'] - 1:
                    print('|\t|')

    def print_frame(self):
        if self.__valid_frame:
            self.__print_header()
            self.__print_structs()
            print()

    def lock_data(self):
        self.__lock.acquire()

    def unlock_data(self):
        self.__lock.release()

    def get_detected_objs(self):
        if self.__valid_frame:
            for s in self.__frame['struct']:
                if s['tag'] == STRUCT_TAG.DETECTED_POINTS:
                    return self.__det_objs_struct
        return None

    def get_range_profile(self):
        if self.__valid_frame:
            for s in self.__frame['struct']:
                if s['tag'] == STRUCT_TAG.RANGE_PROFILE:
                    #  20 * log10( 2.^(logMagRange/2^9) )
                    #  return [20*math.log10(2.**(int(num, 16)/2**9))
                                    #  for num in s['payload'].split(':')]
                    return s['payload']
        return None
