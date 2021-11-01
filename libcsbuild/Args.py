#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import libcsbuild


_WORKING_DIR = '.xdb'
_COMMAND = []


def set_working_dir(working_dir):
    global _WORKING_DIR
    _WORKING_DIR = working_dir


def get_working_dir():
    return _WORKING_DIR


def set_command(command):
    global _COMMAND
    _COMMAND = command


def get_command():
    return _COMMAND


def get_new_file_path(filename):
    return os.path.join(get_working_dir(), filename)
