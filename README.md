# Symibiflow xc7z based automatic test system

## Description

The system is designed for automatic biststream testing on xc7z devices.
Currently the system can be run the [Zybo-Z7](https://reference.digilentinc.com/reference/programmable-logic/zybo-z7/start).
The following sections describe how to prepare test setup and run the tests.

## Test setup

In general the tests can be run on any xc7z device. The tests are run from Linux running on the processing system of the xc7z device.
The following guide assume the system boots from SD Card. Linux distribution used in the system is Arch Linux.

### Prerequisites

Get all the sources:

```  bash
git clone https://github.com/SymbiFlow/symbiflow-xc7z-automatic-tester.git
cd symbiflow-xc7z-automatic-tester
git submodule update --init --recursive
```

Get ARM toolchain:
```  bash
wget https://developer.arm.com/-/media/Files/downloads/gnu-rm/9-2019q4/RC2.1/gcc-arm-none-eabi-9-2019-q4-major-x86_64-linux.tar.bz2
tar -xf gcc-arm-none-eabi-9-2019-q4-major-x86_64-linux.tar.bz2
export PATH=${PWD}/gcc-arm-none-eabi-9-2019-q4-major/bin:$PATH
```

### SD card preparation

Follow the [official guide](https://xilinx-wiki.atlassian.net/wiki/spaces/A/pages/18842385/How+to+format+SD+card+for+SD+boot) to prepare SD card.

### Getting Arch rootfs

Download Arch rootfs with:

``` bash
wget http://de5.mirror.archlinuxarm.org/os/ArchLinuxARM-armv7-latest.tar.gz
```

Unpack the file package onto the ``rootfs`` partition of the SD card:

``` bash
sudo tar -xf ArchLinuxARM-armv7-latest.tar.gz -C /path/to/mountpoint/rootfs
```

### Building U-Boot bootloader

U-Boot sources are fetched as a submodule in the main repo
Building the software:

``` bash
cd u-boot-xlnx
export ARCH=arm
export CROSS_COMPILE=arm-none-eabi-
make zynq_zybo_z7_defconfig
make -j`nproc`
```

Copy the resulting files to the ``boot`` partition of the SD card:

``` bash
cp spl/boot.bin /path/to/mountpoint/boot
cp u-boot.img /path/to/mountpoint/boot
```

### Building Linux kernel

Kernel sources are fetched as a submodule in the main repo
Building the kernel:

``` bash
cd linux-xlnx
export ARCH=arm
export CROSS_COMPILE=arm-none-eabi-
export LOADADDR=0x8000
make xilinx_zynq_defconfig
make -j`nproc` uImage
make -j`nproc` dtbs
make -j`nproc` modules
```

Copy the required files to the SD card:
``` bash
cp arch/arm/boot/uImage /path/to/mountpoint/boot
cp arch/arm/boot/dts/zynq-zybo-z7.dtb /path/to/mountpoint/boot/devicetree.dtb
sudo cp drivers/misci/symbiflow-tester.ko /path/to/mountpoint/rootfs/root
```

### Adding required files to rootfs

Copy the required files to the SD card:

``` bash
sudo cp python/symbiflow_test.py /path/to/mountpoint/rootfs/root
sudo cp -a devmemX /path/to/mountpoint/rootfs/root
sudo cp -a zynq_bootloader /path/to/mountpoint/root
```

## Running the tests

### Booting the device for the first time

Connect Zybo-Z7's USB serial console to the PC.
Insert prepared SD card into the board, set [boot mode to SD](https://reference.digilentinc.com/reference/programmable-logic/zybo-z7/reference-manual#microsd_boot_mode) and power up the board.
Stop U-Boot autoboot by pressing any key during countdown.
In U-Boot's console run the following commands:

```
setenv booargs "root=/dev/mmcblk0p2 rw rootwait"
setenv bootcmd "load mmc 0 0x1000000 uImage && load mmc 0 0x2000000 devicetree.dtb && bootm 0x1000000 - 0x2000000"
saveenv
```

Reset the device and let it boot.
Log into Arch Linux with the following credentials:
```
user: root
pass: root
```

On the first boot it is required to install some additional packages in the system.
To do so, connect the board to Internet and run the following commands:

```
pacman -Syy
pacman -S python make gcc python-pip
pip install fnctl
```

Build and install additional tools:

``` bash
cd /root/devmemX
make && make install
cd /root/zynq_bootloader/bit2bitbin
gcc bit2bitbin.c -o bit2bitbin
cp bit2bitbin /usr/bin
```

### Running the test script

Run the test script with the following command:

``` bash
python symbiflow_test.py --module symbiflow-tester.ko --module_name symbiflow_tester --bitstream top.bit --dev /dev/symbiflow-tester0 --driver_name symbiflow-tester
```

The test will program the FPGA fabric and run two tests:

* Register access test
* PS -> PL interrupts test

The PL fabric implements AXI Lite accessible registers.
The registers can be written and read from the PS7.
The registers are accessible at ``0x40000000`` address.


The first one writes random registers with random data, then reads it back and compare the values.

The second one uses the PL peripheral to generate random number of PS interrupts. PS Linux driver counts them and report back to the test script (via IOCTL).
