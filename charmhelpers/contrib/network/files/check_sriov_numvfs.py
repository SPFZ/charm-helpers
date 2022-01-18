#!/usr/bin/env python3
# Copyright 2014-2022 Canonical Limited.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Check to verify the number of virtual functions (VFs) active on SR-IOV network
interfaces. Based on /sys/class/net/<interface>/device/sriov_numvfs and
/sys/class/net/<interface>/device/sriov_totalvfs.

    usage: check_sriov_numvfs.py [-h] sriov_numvfs [sriov_numvfs ...]

    Check SR-IOV number of virtual functions configuration

    positional arguments:
    sriov_numvfs  format: <interface>:<numvfs>

For each interfaces:numvfs pair given it verifies that:
    1. VFs are enabled
    2. VFs are configured are the same as specified in the check parameter
    3. VFs configured do not exceed the maximum available on the interface

    Non-existent interfaces are not checked.

Example: ./check_sriov_numvfs.py ens3f0:32 ens3f1:32 ens6f0:32 ens6f1:32
"""

import argparse
import os.path
import traceback
import sys


DEVICE_TEMPLATE = "/sys/class/net/{0}"
SRIOV_NUMVFS_TEMPLATE = "/sys/class/net/{0}/device/sriov_numvfs"
SRIOV_TOTALVFS_TEMPLATE = "/sys/class/net/{0}/device/sriov_totalvfs"


class ArgsFormatError(Exception):
    """This indicates argument format that is not supported."""

    pass


def get_interface_setting(file):
    """Return the value content of a setting file as int"""
    with open(file) as f:
        value = f.read()
    return int(value)


def check_interface_numvfs(iface, numvfs):
    """Check SR-IOV numvfs config"""
    sriov_numvfs_path = SRIOV_NUMVFS_TEMPLATE.format(iface)
    sriov_totalvfs_path = SRIOV_TOTALVFS_TEMPLATE.format(iface)
    msg = []

    # Ignore non-existing interfaces
    if not os.path.exists(DEVICE_TEMPLATE.format(iface)):
        return []

    # Ensure that SR-IOV/VT-d and IOMMU are enabled
    if not os.path.exists(sriov_totalvfs_path) or not os.path.exists(sriov_numvfs_path):
        return ["{}: VFs are disabled or not-available".format(iface)]

    # Verify number of virtual functions
    sriov_numvfs = get_interface_setting(sriov_numvfs_path)
    sriov_totalvfs = get_interface_setting(sriov_totalvfs_path)
    if numvfs != sriov_numvfs:
        msg.append(
            "{}: Number of VFs on interface ({}) does not match expected ({})".format(
                iface, sriov_numvfs, numvfs
            )
        )
    if numvfs > sriov_totalvfs:
        msg.append(
            "{}: Maximum number of VFs available on interface ({}) is lower than the expected ({})".format(
                iface, sriov_totalvfs, numvfs
            )
        )
    return msg


def parse_sriov_numvfs(device_numvfs):
    """Parse parameters and check format"""
    msg = "Parameter format must be '<interface>:<numvfs>', e.g. ens3f0:32, given: '{}'".format(
        device_numvfs
    )
    parts = device_numvfs.split(":")
    if (
        len(parts) != 2 or      # exactly 2 parts
        len(parts[0]) < 3 or    # interface name should be at least 3 chars
        len(parts[1]) < 1 or    # numvfs should be at least 1 char
        int(parts[1]) < 0       # numvfs should be a valid int > 0
    ):
        raise ArgsFormatError(msg)
    iface = str(device_numvfs.split(":")[0])
    numvfs = int(device_numvfs.split(":")[1])
    return (iface, numvfs)


def parse_args():
    """Parse command-line options."""
    parser = argparse.ArgumentParser(
        description="Check SR-IOV number of virtual functions configuration"
    )
    parser.add_argument("sriov_numvfs", nargs="+", help="format: <interface>:<numvfs>")
    args = parser.parse_args()
    return args


def main():
    """Parse args and check the sriov numvfs."""
    args = parse_args()
    error_msg = []

    try:
        for device_numvfs in args.sriov_numvfs:
            iface, numvfs = parse_sriov_numvfs(device_numvfs)
            error_msg += check_interface_numvfs(iface, numvfs)
        if error_msg:
            error_list = "\n".join(error_msg)
            print(
                "CRITICAL: {} problems detected\n{}".format(len(error_msg), error_list)
            )
            sys.exit(2)
    except (FileNotFoundError, PermissionError, ValueError, ArgsFormatError) as e:
        msg = "CRITICAL: Exception {} occurred during check: '{}'"
        print(msg.format(e.__class__.__name__, e))
        traceback.print_exc(file=sys.stdout)
        sys.exit(2)
    except:  # noqa: E722
        print("{} raised unknown exception '{}'".format(__file__, sys.exc_info()[0]))
        traceback.print_exc(file=sys.stdout)
        sys.exit(3)

    msg = "OK: sriov_numvfs set to '{}' (non existing interface are ignored)"
    print(msg.format(", ".join(args.sriov_numvfs)))


if __name__ == "__main__":
    main()
