#! /usr/bin/env python

from threading import Thread, Lock


import colorama
from colorama import Fore
colorama.init(autoreset=True)


# Thread-safe print
_print = print
_print_lock = Lock()
def print(*args, **kwargs):
    with _print_lock:
        _print(*args, **kwargs)


# Thread wrapper
def threaded(fn):
    def wrapper(*args, **kwargs):
        thread = Thread(target=fn, args=args, kwargs=kwargs)
        #  thread.daemon = True
        thread.start()
        return thread
    return wrapper


def error(msg, **kwargs):
    print(Fore.RED + msg, **kwargs)


def warning(msg, **kwargs):
    print(Fore.YELLOW + msg, **kwargs)
