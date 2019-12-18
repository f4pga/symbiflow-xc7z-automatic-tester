#!/usr/bin/env python3

import random
import os
import subprocess
import sys
import fcntl
import time
import argparse

TEST_ADDRESS_SPACE = 0x100
TEST_IP_BASE = 0x40000000
TEST_IP_REGS_NO = 8
TEST_IP_GP_REGS_OFFS = 2

TEST_IP_CTRL_REG = 0
TEST_IP_IRQ_TRIG = (1 << 4)

TEST_IP_GET_IRQ_COUNT = 0


class Devmem:
    def __init__(self, base):
        self.base = base

    def read_dw(self, offset):
        addr = self.base + offset
        value = subprocess.check_output(["devmem2", "w", str(hex(addr))])
        return int(value, 16)

    def write_dw(self, offset, val):
        addr = self.base + offset
        subprocess.run(["devmem2", "w", str(hex(addr)), str(hex(val))])


class Bitstream:
    def __init__(self, path, bit2bin="bit2bitbin", partial=0):
        assert path.endswith(".bit"), "Bistream file should"
        " have .bit extension"

        self.path = path
        self.partial = partial
        self.bit2bin = bit2bin
        self.firmware_name = os.path.basename(path)+".bin"
        self.fpga_man_path = "/sys/class/fpga_manager/fpga0/"
        self.flags = self.fpga_man_path + "flags"
        self.firmware = self.fpga_man_path + "firmware"

    def generate_bin(self):
        subprocess.run([self.bit2bin, self.path,
                        "/lib/firmware/"+self.firmware_name])

    def program(self):
        print("name:", self.firmware_name)
        with open(self.flags, "w") as fp:
            fp.write("{}".format(str(self.partial)))

        with open(self.firmware, "w") as fp:
            fp.write("{}".format(str(self.firmware_name)))


class Register:
    def __init__(self, base_addr):
        self.base_addr = base_addr
        self.mem = Devmem(base_addr)

    def read_reg(self, regnum):
        reg_offs = regnum * 4
        return self.mem.read_dw(reg_offs)

    def write_reg(self, regnum, value):
        reg_offs = regnum * 4
        self.mem.write_dw(reg_offs, value)


class DriverModule:
    def __init__(self, module_path, module_name, device_name):
        self.module_path = module_path
        self.module_name = module_name
        self.device_name = device_name
        modules = subprocess.check_output(["lsmod"])
        self.loaded = self.module_name in str(modules)

    def load(self):
        subprocess.run(["insmod", self.module_path])
        self.loaded = True

    def unload(self):
        subprocess.run(["rmmod", self.module_name])
        self.loaded = False

    def reload(self):
        if self.loaded:
            self.unload()
        self.load()

    def is_irq_registered(self):
        with open("/proc/interrupts", "r") as fp:
            devices = fp.read()

        return self.device_name in devices


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--module", required=True,
                        help="Path to test kernel module")
    parser.add_argument("--module_name", required=True,
                        help="Test driver module name")
    parser.add_argument("--driver_name", required=True,
                        help="Test driver registration name")
    parser.add_argument("--bitstream", required=True,
                        help="Path to test bistream file")
    parser.add_argument("--dev", required=True,
                        help="Path to test driver device file")
    parser.add_argument("--bit2bin", required=False,
                        help="Path to bit2bin application, if not provided"
                             "assuming the app is in PATH")

    args = parser.parse_args()

    bit2bin = "bit2bitbin"
    if args.bit2bin is not None:
        bit2bin = args.bit2bin

    module = DriverModule(args.module, args.module_name, args.driver_name)
    bs = Bitstream(args.bitstream, bit2bin)
    bs.generate_bin()
    bs.program()

    reg = Register(TEST_IP_BASE)
    for t in range(0, 100):
        val = int(random.randrange(0xFFFFFFFF))
        regno = random.randrange(TEST_IP_GP_REGS_OFFS, TEST_IP_REGS_NO)
        reg.write_reg(regno, val)
        val1 = reg.read_reg(regno)
        assert val == val1, \
            "Register value mismatch got {}, should be {}".format(
                    hex(val), hex(val1))

    print("Reg read/write test passed")

    interrupts_count = int(random.randrange(100))
    module.reload()
    # Give it some time to load
    got_device = False
    for t in range(0, 10):
        time.sleep(5)
        if module.is_irq_registered():
            got_device = True
            break

    if not got_device:
        print("Timeout waiting for device")
        sys.exit(1)

    for i in range(0, interrupts_count):
        reg.write_reg(TEST_IP_CTRL_REG, TEST_IP_IRQ_TRIG)

    with open(args.dev, "w") as fp:
        real_interrupts_count = fcntl.ioctl(fp, TEST_IP_GET_IRQ_COUNT)

    assert interrupts_count == real_interrupts_count, \
        "Interrupts count mismatch. Was {}, should be {}".format(
            real_interrupts_count, interrupts_count)

    print("Interrupts test passed")


if __name__ == "__main__":
    main()
