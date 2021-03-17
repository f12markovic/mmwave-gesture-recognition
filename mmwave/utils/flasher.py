#! /usr/bin/env python

import os
import time
import struct

from tqdm import tqdm

from mmwave.utils.utility_functions import error

import colorama
from colorama import Fore
colorama.init(autoreset=True)


class OPCODE:
    SYNC              = struct.pack('B', 0xAA)
    ACK               = struct.pack('B', 0xCC)
    NACK              = struct.pack('B', 0x33)
    PING              = struct.pack('B', 0x20)
    OPEN_FILE         = struct.pack('B', 0x21)
    CLOSE_FILE        = struct.pack('B', 0x22)
    GET_STATUS        = struct.pack('B', 0x23)
    WRITE_FILE        = struct.pack('B', 0x24)
    WRITE_FILE_RAM    = struct.pack('B', 0x26)
    DISCONNECT        = struct.pack('B', 0x27)
    ERASE             = struct.pack('B', 0x28)
    ERASE_FILE        = struct.pack('B', 0x2E)
    GET_VERSION       = struct.pack('B', 0x2F)

    RET_SUCCESS             = struct.pack('B', 0x40)
    RET_ACCESS_IN_PROGRESS  = struct.pack('B', 0x4B)

    # to specify different device variants
    IS_AWR12XX = struct.pack('B', 0x00)
    IS_AWR14XX = struct.pack('B', 0x01)
    IS_AWR16XX = struct.pack('B', 0x03)
    IS_AWR17XX = struct.pack('B', 0x10)


class CMD:
    def __init__(self, opcode, data=None):
        self.CODE = opcode

        if data is not None:
            self.CODE += data

        self.SIZE = struct.pack('>H', (len(self.CODE)-1+3))
        self.CHECKSUM = struct.pack('B', sum(self.CODE) & 0xFF)
        if opcode in [OPCODE.PING, OPCODE.GET_VERSION]:
            self.timeout = 3
        else:
            self.timeout = 60


class Flasher:
    BLOCK_SIZE = 0xF0
    MAX_FILE_SIZE = 1024**2

    FILES = {
        'RadarSS_BUILD':    struct.pack('>I', 0),
        'CALIB_DATA':       struct.pack('>I', 1),
        'CONFIG_INFO':      struct.pack('>I', 2),
        'MSS_BUILD':        struct.pack('>I', 3),
        'META_IMAGE1':      struct.pack('>I', 4),
        'META_IMAGE2':      struct.pack('>I', 5),
        'META_IMAGE3':      struct.pack('>I', 6),
        'META_IMAGE4':      struct.pack('>I', 7)
    }

    STORAGES = {
        'SDRAM':    struct.pack('>I', 0),
        'FLASH':    struct.pack('>I', 1),
        'SFLASH':   struct.pack('>I', 2),
        'EEPROM':   struct.pack('>I', 3),
        'SRAM':     struct.pack('>I', 4)
    }

    def __init__(self, connection):
        self.start_time = 0
        self.connection = connection

        # Set connection
        self.connection.cli_port.send_break(0.1)
        self.connection.cli_port.flushInput()
        self.connection.cli_port.flushOutput()

    def send_packet(self, command):
        self.connection.send_cmd(OPCODE.SYNC, size=0)
        self.connection.send_cmd(command.SIZE, size=0)
        self.connection.send_cmd(command.CHECKSUM, size=0)
        self.connection.send_cmd(command.CODE, size=0)

    def send_cmd(self, command, get_status=False, resp=True):
        self.send_packet(command)
        if not self.get_ack(command.timeout):
            error('Command was not successful!')
            return None

        if get_status:
            response = self.send_packet(CMD(OPCODE.GET_STATUS))

        if resp:
            response = self.get_response()
            return response
        else:
            return True

    def get_response(self):
        header = self.connection.get_cmd(3)
        packet_size, checksum  = struct.unpack('>HB', header)
        packet_size -= 2 # Compensate for the header

        payload = self.connection.get_cmd(packet_size)

        self.connection.send_cmd(OPCODE.ACK, size=0) # Ack the packet

        calculated_checksum = sum(payload) & 0xff
        if (calculated_checksum != checksum):
            error('Checksum error on received packet.')
            return None

        return payload

    def get_ack(self, timeout):
        length = b''
        while length == b'':
            length = self.connection.get_cmd(2)
            time.sleep(0.01)

        self.connection.get_cmd(1) # Checksum
        self.connection.get_cmd(1) # 0x00
        response = self.connection.get_cmd(1)

        while (not ((response == OPCODE.ACK) or
                    (response == OPCODE.NACK))):
            if self.start_time == 0:
                self.start_time = time.time()

            if time.time() - self.start_time > timeout:
                response = None
                break

            response = self.connection.get_cmd(1)
            time.sleep(0.01)

        self.start_time = 0

        if (response == OPCODE.ACK):
            return True
        elif (response == OPCODE.ACK):
            error('Received NACK')
            return False
        else:
            error('Received unexpected data or timeout!')
            return False

    def erase(self, storage='SFLASH', location_offset=0, capacity=0):
        data = (Flasher.STORAGES[storage] +
                struct.pack('>I', location_offset) +
                struct.pack('>I', capacity))

        self.send_cmd(CMD(OPCODE.ERASE, data=data), resp=False)

    def flash(self, files, file_id=4, storage='SFLASH', mirror_enabled=0, erase=False):
        if not isinstance(files, list):
            files = [files]

        if erase:
            print('Formating flash...', end='')
            self.erase()
            print('%sDone.' % Fore.GREEN)

        for file in files:
            file_size = os.path.getsize(file)
            print('Writing %s [%d bytes]' %
                    (list(Flasher.FILES)[file_id], file_size))

            if (file_size < 0) and (file_size > Flasher.MAX_FILE_SIZE):
                error('Invalid file size')
                return False

            with open(file, 'rb') as f:
                resp = self.send_cmd(CMD(OPCODE.OPEN_FILE,
                                         data=(struct.pack('>I', file_size) +
                                               Flasher.STORAGES[storage] +
                                               list(Flasher.FILES.values())[file_id] +
                                               struct.pack('>I', mirror_enabled))),
                                         get_status=True)
                if resp != OPCODE.RET_SUCCESS:
                    error('Opening file failed.')
                    return False

                pbar = tqdm(total=file_size//Flasher.BLOCK_SIZE+1, desc='Blocks')
                offset = 0
                while offset < file_size:
                    block = f.read(Flasher.BLOCK_SIZE)
                    if (storage == 'SRAM'):
                        resp = self.send_cmd(CMD(OPCODE.WRITE_FILE_RAM, data=block),
                                             get_status=True)
                    else:
                        resp = self.send_cmd(CMD(OPCODE.WRITE_FILE, data=block),
                                             get_status=True)

                    if resp != OPCODE.RET_SUCCESS:
                        error('Sending file failed.')
                        return False

                    offset += len(block)
                    pbar.update(1)
            pbar.close()

            self.send_cmd(CMD(OPCODE.CLOSE_FILE,
                              data=list(Flasher.FILES.values())[file_id]),
                          resp=False)

            file_id += 1
            if file_id > 7:
                break

        return True
