#!/bin/bash
# Copyright (C) 2020-2021  The Project X-Ray Authors.
#
# Use of this source code is governed by a ISC-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/ISC
#
# SPDX-License-Identifier: ISC

WORKDIR=${PWD}

# Getting the ARM toolchain
wget -qO- https://developer.arm.com/-/media/Files/downloads/gnu-rm/9-2019q4/RC2.1/gcc-arm-none-eabi-9-2019-q4-major-x86_64-linux.tar.bz2 | tar -xj
export PATH=${PWD}/gcc-arm-none-eabi-9-2019-q4-major/bin:$PATH

# Create artifacts directory
mkdir root boot

# Build U-boot bootloader
pushd u-boot-xlnx
export ARCH=arm
export CROSS_COMPILE=arm-none-eabi-
make zynq_zybo_z7_defconfig
make -j`nproc`

cp spl/boot.bin u-boot.img ${WORKDIR}/boot
popd

# Build Linux kernel
pushd linux-xlnx
git apply ../linux/0001-Add-symbiflow-tester-driver.patch
export ARCH=arm
export CROSS_COMPILE=arm-none-eabi-
export LOADADDR=0x8000
make xilinx_zynq_defconfig
make -j`nproc` uImage
make -j`nproc` dtbs
make -j`nproc` modules

cp arch/arm/boot/uImage ${WORKDIR}/boot
cp arch/arm/boot/dts/zynq-zybo-z7.dtb ${WORKDIR}/boot/devicetree.dtb
cp drivers/misc/symbiflow-tester.ko ${WORKDIR}/root
popd

# Adding required files to rootfs
cp -a python/symbiflow_test.py devmemX zynq_bootloader ${WORKDIR}/root
