#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import argparse

import libcsbuild
import codescroll


def display_first_usage():
    print()


def capture_common():
    parser = argparse.ArgumentParser(add_help=False, usage="csbuild capture [BUILD_COMMAND]")
    try:
        libcsbuild.set_command(sys.argv[2:])

    except Exception as e:
        if str(e) != '':
            libcsbuild.error_message(str(e))
        parser.print_help()
        return False

    libcsbuild.set_working_dir(os.path.join(os.path.abspath(os.curdir), '.xdb'))
    os.environ['STATICFILE_WORKDIR'] = libcsbuild.get_working_dir()

    # LDH, 워킹 디렉토리 없으면 생성
    if not os.path.exists(libcsbuild.get_working_dir()):
        os.makedirs(libcsbuild.get_working_dir())


def capture_processing():
    capture_common()
    return codescroll.run()


def capture_post_only_processing():
    return codescroll.run_post()
