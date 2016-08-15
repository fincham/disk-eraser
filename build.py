#!/usr/bin/env python
#
# Copyright (c) 2015 Catalyst.net Ltd
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import argparse
import os
import random
import shutil
import stat
import StringIO
import subprocess
import sys
import tempfile

"""
Produce an initrd image which automatically erases all disks in the local machine.

Michael Fincham <michael.fincham@catalyst.net.nz>
"""

def find(root):
    for root, dirs, files in os.walk(root):
        print dirs
        print files

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('initrd', help='path to initrd.gz file to repack')

    args = parser.parse_args()

    initrd_path = os.path.abspath(args.initrd)
    original_cwd = os.getcwd()

    # XXX this script is very much a weekend throw-together to test some ideas. considerable
    # further work is required.
    # note: to unfreeze disks "+20" can be written to the RTC wakealarm then the system put in to suspend mode
    shell = """#!/bin/sh

modprobe -v i8042 || true
modprobe -v atkbd || true
modprobe -v ehci-pci || true
modprobe -v ehci-orion || true
modprobe -v ehci-hcd || true
modprobe -v uhci-hcd || true
modprobe -v ohci-hcd || true
modprobe -v usbhid || true

clear
echo "Fincham's automated disk eraser"
echo "==============================="
echo -n "Detecting disks... "

mkdir -p /tmp/disks
egrep -v "#blocks|fd0|^$" /proc/partitions | sed -e 's/.* //' | while read device; do
    if hdparm -I /dev/$device 2>/dev/null | grep "non-removable media" >/dev/null; then
        serial="`hdparm -I /dev/$device | grep "Serial Number" | sed -e 's/.* //'`"
        if test ! -f "/tmp/disks/$serial"; then
            echo "/dev/$device" > "/tmp/disks/$serial"
            hdparm -I "/dev/$device" >> "/tmp/disks/$serial"
        fi
    fi
done

echo "done"
echo ""

echo "These disks have been detected:"

any=0
cd /tmp/disks
ls -1 | while read serial; do
    any=1
    size="`grep "device size" $serial | grep "1024" | sed -e 's/[^:]*: *//'`"
    device="`head -n 1 $serial`"

    if grep "not" $serial | grep "frozen" > /dev/null; then
        frozen=0
    else
        frozen=1
    fi

    if grep "SECURITY ERASE UNIT" $serial > /dev/null; then
        secure_erase=1
    else
        secure_erase=0
    fi

    if grep "ENHANCED SECURITY ERASE UNIT" $serial > /dev/null; then
        enhanced_secure_erase=1
    else
        enhanced_secure_erase=0
    fi

    echo -n "$size, $serial: "

    if test $enhanced_secure_erase -eq 1; then
        echo -n "enhanced secure erase supported"
    else
        if test $secure_erase -eq 1; then
            echo -n "secure erase supported"
        fi
    fi

    if test $frozen -eq 1; then
        echo ", but frozen."
    else
        echo "."
    fi

done

if test `ls -1 /tmp/disks | wc -l` -eq 0; then
    echo "No disks could be identified, falling back to nwipe's automatic mode."
fi

echo ""
echo "Secure erase is disabled, falling back to software erase."

abort=""
for s in `seq 30 -1 0`; do
    echo -n "Starting disk erase in $s seconds, press ESC to abort..."
    read -n1 -t1 abort
    if test ! -z "$abort"; then
        abort="aborted"
        echo -n -e "\033[2K\r"
        echo "Aborted."
        break
    fi
    echo -n -e "\033[2K\r"
done


if test -z "$abort"; then
    echo "Starting software erase..."
    nwipe --nogui --autonuke `head -n1 -q /tmp/disks/* 2>/dev/null`
    echo "Software erase complete. Press enter to reboot."
    read -n1 reboot
else
    echo "Starting a shell..."
    setsid cttyhack sh
fi

echo b > /proc/sysrq-trigger
"""

    order = """/scripts/local-top/eraser
    """

    working_directory = tempfile.mkdtemp()
    os.chdir(working_directory)

    with open('initrd.cpio','wb') as initrd_cpio:
        print "Unpacking initrd..."
        subprocess.check_call(("gzip -cd %s" % initrd_path).split(), stdout=initrd_cpio)

    with open('initrd.cpio','rb') as initrd_cpio:
        subprocess.check_call(("cpio -id").split(), stdin=initrd_cpio)

    print ""
    print "Re-packing initrd..."

    os.unlink('initrd.cpio')
    shutil.copy('/sbin/hdparm', 'sbin/hdparm')
    shutil.copy('/usr/sbin/nwipe', 'sbin/nwipe')

    nwipe_deps = [
        '/lib/x86_64-linux-gnu/libpthread.so.0',
        '/lib/x86_64-linux-gnu/libparted.so.2',
        '/usr/lib/x86_64-linux-gnu/libpanel.so.5',
        '/lib/x86_64-linux-gnu/libncurses.so.5',
        '/lib/x86_64-linux-gnu/libtinfo.so.5',
        '/lib/x86_64-linux-gnu/libuuid.so.1',
        '/lib/x86_64-linux-gnu/libdl.so.2',
        '/lib/x86_64-linux-gnu/libdevmapper.so.1.02.1',
        '/lib/x86_64-linux-gnu/libblkid.so.1',
        '/lib/x86_64-linux-gnu/libselinux.so.1',
        '/lib/x86_64-linux-gnu/libudev.so.1',
        '/lib/x86_64-linux-gnu/libpcre.so.3',
        '/lib/x86_64-linux-gnu/librt.so.1',
        '/lib/x86_64-linux-gnu/libgcc_s.so.1'
    ]

    for dep in nwipe_deps:
        shutil.copy(dep, 'lib/x86_64-linux-gnu/%s' % dep.split('/')[-1])

    with open('scripts/local-top/eraser', 'w') as shell_file:
        shell_file.write(shell)
    os.chmod('scripts/local-top/eraser', 0o755)
    with open('scripts/local-top/ORDER', 'w') as order_file:
        order_file.write(order)

    file_list = subprocess.check_output("find .".split())

    with open('initrd.cpio', 'w') as initrd_cpio:
        cpio_process = subprocess.Popen('cpio -H newc -o'.split(), stdin=subprocess.PIPE, stdout=initrd_cpio)
        cpio_process.communicate(file_list)

    with open(initrd_path,'wb') as initrd_cpio:
        subprocess.check_call("gzip -c initrd.cpio".split(), stdout=initrd_cpio)

    os.chdir(original_cwd)
    shutil.rmtree(working_directory)
