#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse

import libcsbuild
import codescroll
import codescroll.strace
import codescroll.build_normal


def display_first_usage():
    print()


def capture_processing():
    parser = argparse.ArgumentParser(add_help=False, usage="csbuild capture [-e|--edg] [-v|--valid] [BUILD_COMMAND]")
    try:
        parser.add_argument("-h", "--help", action='help', help="Show the command of csbuild capture mode")
        parser.add_argument('command', metavar='BUILD_COMMAND', type=str, nargs='*', help="Command to build source or script")
        args = parser.parse_args(sys.argv[2:])

        libcsbuild.set_command(args.command)

    except Exception as e:
        if str(e) != '':
            libcsbuild.error_message(str(e))
        parser.print_help()
        return False

    os.environ['STATICFILE_WORKDIR'] = libcsbuild.get_working_dir()

    # LDH, 워킹 디렉토리 없으면 생성
    if not os.path.exists(libcsbuild.get_working_dir()):
        os.makedirs(libcsbuild.get_working_dir())

    return codescroll.build_normal.run()
