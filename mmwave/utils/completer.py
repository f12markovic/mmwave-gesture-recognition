#! /usr/bin/env python

import readline
import glob


class Completer(object):
    def __init__(self, list):
        def list_completer(text, state):
            line = readline.get_line_buffer()
            if not line:
                return [c + ' ' for c in list][state]
            else:
                return [c + ' ' for c in list if c.startswith(line)][state]
        self.list_completer = list_completer

    def path_completer(self, text, state):
        line = readline.get_line_buffer().split()
        return [x for x in glob.glob(text + '*')][state]
