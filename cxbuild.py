#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import multiprocessing
import sys
import time
import signal
import traceback

import libcsbuild
import processor


def initialize():
    # wtrace, strace 등을 호출 할수 있도록 home directory 등록
    libcsbuild.initialize_environment_variables()
    # 인터럽트 시그널 발생시켜도 에러 메시지 띄울 수 있도록 처리
    signal.signal(signal.SIGINT, receive_signal)


options = {
    'capture': {
        "function": processor.capture_processing,
        'group': 'legacy',
        'help': 'Performs user commands to capture compilation information and only save it local storage area'},
    'captured': {
        "function": processor.capture_post_only_processing,
        'group': 'legacy',
        'help': 'DO NOT performs user commands, but process post process phase'},
}

prints = ['legacy']


def display_general_usage():
    libcsbuild.kindness_message("If you want to run your command, please run like this:")
    libcsbuild.command_message("    csbuild command [command option]")
    print()
    libcsbuild.kindness_message("These are csbuild commands used in various situations:")
    for option in options.keys():
        if options[option]['group'] in prints:
            libcsbuild.command_message('    %-10s\t%s' % (option, options[option]['help']))
    print()


def receive_signal(signum, frame):
    libcsbuild.kindness_message("Interrupt signal received.")
    libcsbuild.kindness_message("Aborted.")
    # STATIC-1720, csbuild.lock 파일 unlock 후 삭제
    exit(1)


def unexpected_error_message():
    libcsbuild.error_message("Unexpected error has occurred.")
    print_error_message()


def print_error_message():
    libcsbuild.error_message("Please contact customer support after preserving your current status and logs.")


def get_trace_back():
    lines = traceback.format_exc().strip().split('\n')
    rl = [lines[-1]]
    lines = lines[1:-1]
    lines.reverse()
    for i in range(0, len(lines), 2):
        if i + 1 >= len(lines):
            rl.append('* \t%s' % (lines[i].strip()))
        else:
            rl.append('* \t%s at %s' % (lines[i].strip(), lines[i + 1].strip()))
    return '\n'.join(rl)


def main_driver():
    initialize()
    libcsbuild.kindness_message(f"eXtension of Compilation Database")

    if len(sys.argv) > 1 and sys.argv[1] in options.keys():
        return options[sys.argv[1]]['function']()
    else:
        display_general_usage()
        print()
        return False


if __name__ == "__main__":
    multiprocessing.freeze_support()
    start_time = time.time()
    try:
        if main_driver():
            sys.exit(0)
        else:
            libcsbuild.set_return_value(1)
            sys.exit(1)  # something failed
    except SystemExit as e:
        if not e.code == 0:
            if '--help' not in sys.argv and sys.argv[1] not in ['capture']:
                print_error_message()
    except:
        print(get_trace_back())
        unexpected_error_message()
    finally:
        import cslib
        end_time = time.time()
        elapsed = end_time - start_time
        elapsed_time = time.strftime("%H:%M:%S", time.gmtime(elapsed))
        libcsbuild.kindness_message("Finished(%s)" % elapsed_time)
        # STATIC-1720, csbuild.lock 파일 unlock 후 삭제
        if libcsbuild.get_return_value() == 0:
            sys.exit(0)
        else:
            sys.exit(libcsbuild.get_return_value())
