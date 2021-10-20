#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import libcsbuild

CSBUILD_HOME = os.path.dirname(os.path.realpath(__file__))


def csbuild_home_directory():
    if os.getenv('CSBUILD_HOME_DIR') is not None:
        return os.getenv('CSBUILD_HOME_DIR').replace('"', '')
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.getenv('CSBUILD_HOME', CSBUILD_HOME)


def initialize_environment_variables():
    os.environ['PATH'] = csbuild_home_directory() + os.pathsep + os.environ['PATH']
    os.environ['CSBUILD_BUILD_ROOT'] = os.getcwd()


def csbuild_build_root():
    return os.environ['CSBUILD_BUILD_ROOT']

def is_64bit_os():
    return os.getenv('PROGRAMFILES(X86)') is not None
