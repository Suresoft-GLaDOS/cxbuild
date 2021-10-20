#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import colorama
from colorama import Fore, Back, Style

return_value = 0
colorama.init()


def kindness_message(message):
    print("%s> %s%s" % (Fore.GREEN, message, Fore.RESET))
    msg = ">  {0}".format(message)


def warning_message(message, log_path=None):
    print("%s   -- %s%s" % (Fore.YELLOW, message, Fore.RESET))
    msg = "   -- {0}".format(message)


def error_message(message):
    print("%s   !! %s !!%s" % (Fore.RED, message, Fore.RESET))
    msg = "   !! {0} !!".format(message)
    set_return_value(1)


def command_message(message):
    print("%s%s%s" % (Fore.YELLOW, message, Fore.RESET))
    msg = "{0}".format(message)


def info_message(message):
    print("  > %s%s%s" % (Fore.CYAN, message, Fore.RESET))
    msg = "  > {0}".format(message)


def element_message(message, log_path=None):
    print("%s   - %s%s" % (Fore.CYAN, message, Fore.RESET))
    msg = "   - {0}".format(message)


def step_message(message):
    print("-- %s[%s]%s" % (Fore.YELLOW, message, Fore.RESET))
    msg = "-- [{0}]".format(message)


def debug_message(message):
    import cslib
    if not cslib.is_debug_mode():
        return
    print("[DEBUG] %s%s%s" % (Fore.MAGENTA, message, Fore.RESET))
    msg = "[DEBUG] {0}".format(message)


def set_return_value(set_value):
    global return_value
    if return_value == 123:
        return
    return_value = set_value


def get_return_value():
    global return_value
    return return_value


