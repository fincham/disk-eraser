# disk-eraser

Builds a Debian initrd image containing nwipe configured to erase all available disks when booted.

## Usage

Script must be run with the path to a copy of a suitable Debian initrd image, for instance:

<pre>
fincham@build:~$ sudo apt-get install nwipe
fincham@build:~$ cp /boot/initrd.img-`uname -r` ./initrd.img
fincham@build:~$ cp /boot/vmlinuz-`uname -r` ./vmlinuz

fincham@build:~$ ./build.py initrd.img
Unpacking initrd...
113592 blocks

Re-packing initrd...
115023 blocks
</pre>

The resulting <tt>initrd.img</tt> can then be booted along with a matching kernel. For instance to boot from <tt>pxelinux</tt>:

<pre>
LABEL disk-eraser
    LINUX vmlinuz
    INITRD initrd.img
    APPEND root=/dev/ram0 quiet
</pre>

The image may also be booted using <tt>kexec</tt> to remotely erase a machine over SSH, though care must be taken to ensure the machine is really erased since no feedback will be possible once the boot process begins.

Once the kernel has been loaded, <tt>nwipe</tt> will be started in automatic mode after a 30 second delay.

An attempt is made to only erase devices that report a serial number when interrogated with <tt>hdparm</tt>. If no devices are found this way then detection of the drives to be erased will be handed over to <tt>nwipe</tt>. This may cause e.g. USB sticks inserted in the machine to be erased as well.

## Caveats

Currently the script expects to be run on Debian Jessie, as it contains a static list of the dependencies needed for <tt>nwipe</tt>. This will be fixed in a future release. The resulting initrd image and kernel however may be used on any machine, not just Debian Jessie systems.

Future versions of this software will use ATA Secure Erase (including unfreezing disks as needed) as a preference, before falling back to <tt>nwipe</tt>. This is not yet implemented.
