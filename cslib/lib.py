#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import cslib

fake_chdir = None
def set_fake_chdir(f):
    global fake_chdir
    fake_chdir = f


def chdir(args):
    if cslib.is_unit_testing():
        if fake_chdir is not None:
            return fake_chdir(args)
    else:
        if not os.path.exists(args):
            args = args.replace(' (deleted)', '') # cstrace 가 출력한 proc/pid/cwd 에 ' (deleted)' 가 끝에 붙는 경우가 있음
        if os.path.exists(args):
            return os.chdir(args)
        return True


fake_path_exists = None
def set_fake_path_exists(f):
    global fake_path_exists
    fake_path_exists = f


def exists(args: str):
    if cslib.is_unit_testing():
        if fake_path_exists is not None:
            if cslib.is_windows():
                if args[0].isalpha() and args[1] == ":":
                    return fake_path_exists(args)
            return False
    return os.path.exists(args)
