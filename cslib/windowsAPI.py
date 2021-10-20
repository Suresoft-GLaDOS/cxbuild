#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

import cslib


def get_drive_mapped_path_dict():
    def get_mapped_path_for_drive(drive):
        # use window API (WNetGetConnectionW)
        try:
            import ctypes
            from ctypes import wintypes

            mpr = ctypes.WinDLL('mpr')
            ERROR_SUCCESS = 0x0000
            ERROR_MORE_DATA = 0x00EA
            wintypes.LPDWORD = ctypes.POINTER(wintypes.DWORD)
            mpr.WNetGetConnectionW.restype = wintypes.DWORD
            mpr.WNetGetConnectionW.argtypes = (wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.LPDWORD)
            length = (wintypes.DWORD * 1)()

            result = mpr.WNetGetConnectionW(drive, None, length)
            if result != ERROR_MORE_DATA:
                return ''
            remote_name = (wintypes.WCHAR * length[0])()
            result = mpr.WNetGetConnectionW(drive, remote_name, length)
            if result != ERROR_SUCCESS:
                return ''
            return remote_name.value.replace('\\\\', '')
        except Exception:
            import libcsbuild
            libcsbuild.write_csbuild_log('EXCEPTION_IN_PROCESSING_NETWORK_DRIVE: %s' % drive)
            return ''

    drive_mapped_path_dict = {}
    if not cslib.is_windows():
        return drive_mapped_path_dict

    import win32api
    import libcsbuild
    drive_letter_list = [drive_letter.replace('\\', '') for drive_letter in
                         win32api.GetLogicalDriveStrings().split('\000')[:-1] if drive_letter != '']
    for drive_letter in drive_letter_list:
        key = get_mapped_path_for_drive(drive_letter)
        if key == '':
            continue
        libcsbuild.write_csbuild_log('network_drive: %s, path: %s' % (drive_letter, key))
        drive_mapped_path_dict[key] = drive_letter
    libcsbuild.write_csbuild_log(str(drive_mapped_path_dict))
    return drive_mapped_path_dict


def convert_network_drive_path(open_file, mapped_dict):
    unc_prefix = '\\Device\\Mup'
    if not cslib.is_windows() or not open_file.startswith(unc_prefix):
        return open_file
    for key in mapped_dict.keys():
        inx = open_file.find(key)
        if inx == -1:
            continue
        import libcsbuild
        libcsbuild.write_csbuild_log(
            '%s -> %s' % (open_file, os.path.join(mapped_dict[key], open_file[inx + len(key):])))
        open_file = os.path.join(mapped_dict[key], open_file[inx + len(key):])
    return open_file
