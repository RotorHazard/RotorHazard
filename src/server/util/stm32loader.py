# Authors: Ivan A-R, Floris Lambrechts
# GitHub repository: https://github.com/florisla/stm32loader
#
# This file is part of stm32loader.
#
# stm32loader is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 3, or (at your option) any later
# version.
#
# stm32loader is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License
# along with stm32loader; see the file LICENSE.  If not see
# <http://www.gnu.org/licenses/>.

"""Talk to an STM32 native bootloader (see ST AN3155)."""


from __future__ import print_function

import math
import operator
import struct
import sys
import time
import traceback
from functools import reduce

Console_output_fn = print

CHIP_IDS = {
    # see ST AN2606 Table 136 Bootloader device-dependent parameters
    # 16 to 32 KiB
    0x412: "STM32F10x Low-density",
    0x444: "STM32F03xx4/6",
    # 64 to 128 KiB
    0x410: "STM32F10x Medium-density",
    0x420: "STM32F10x Medium-density value line",
    0x460: "STM32G0x1",
    # 256 to 512 KiB (5128 Kbyte is probably a typo?)
    0x414: "STM32F10x High-density",
    0x428: "STM32F10x High-density value line",
    # 768 to 1024 KiB
    0x430: "STM3210xx XL-density",
    # flash size to be looked up
    0x416: "STM32L1xxx6(8/B) Medium-density ultralow power line",
    0x411: "STM32F2xxx",
    0x433: "STM32F4xxD/E",
    0x431: "STM32F411xx",
    # STM32F3
    0x432: "STM32F373xx/378xx",
    0x422: "STM32F302xB(C)/303xB(C)/358xx",
    0x439: "STM32F301xx/302x4(6/8)/318xx",
    0x438: "STM32F303x4(6/8)/334xx/328xx",
    0x446: "STM32F302xD(E)/303xD(E)/398xx",
    # RM0090 in ( 38.6.1 MCU device ID code )
    0x413: "STM32F405xx/07xx and STM32F415xx/17xx",
    0x419: "STM32F42xxx and STM32F43xxx",
    0x449: "STM32F74xxx/75xxx",
    0x451: "STM32F76xxx/77xxx",
    # RM0394 46.6.1 MCU device ID code
    0x435: "STM32L4xx",
    # see ST AN4872
    # requires parity None
    0x11103: "BlueNRG",
    # STM32F0 RM0091 Table 136. DEV_ID and REV_ID field values
    0x440: "STM32F030x8",
    0x445: "STM32F070x6",
    0x448: "STM32F070xB",
    0x442: "STM32F030xC",
    # Cortex-M0 MCU with hardware TCP/IP and MAC
    # (SweetPeas custom bootloader)
    0x801: "Wiznet W7500",
}


class Stm32LoaderError(Exception):
    """Generic exception type for errors occurring in stm32loader."""


class CommandError(Stm32LoaderError, IOError):
    """Exception: a command in the STM32 native bootloader failed."""


class PageIndexError(Stm32LoaderError, ValueError):
    """Exception: invalid page index given."""


class DataLengthError(Stm32LoaderError, ValueError):
    """Exception: invalid data length given."""


class DataMismatchError(Stm32LoaderError):
    """Exception: data comparison failed."""


class ShowProgress:
    """
    Show progress through a progress bar, as a context manager.

    Return the progress bar object on context enter, allowing the
    caller to to call next().

    Allow to supply the desired progress bar as None, to disable
    progress bar output.
    """

    class _NoProgressBar:
        """
        Stub to replace a real progress.bar.Bar.

        Use this if you don't want progress bar output, or if
        there's an ImportError of progress module.
        """

        def next(self):  # noqa
            """Do nothing; be compatible to progress.bar.Bar."""

        def finish(self):
            """Do nothing; be compatible to progress.bar.Bar."""

    def __init__(self, progress_bar_type):
        """
        Construct the context manager object.

        :param progress_bar_type type: Type of progress bar to use.
           Set to None if you don't want progress bar output.
        """
        self.progress_bar_type = progress_bar_type
        self.progress_bar = None

    def __call__(self, message, maximum):
        """
        Return a context manager for a progress bar.

        :param str message: Message to show next to the progress bar.
        :param int maximum: Maximum value of the progress bar (value at 100%).
          E.g. 256.
        :return ShowProgress: Context manager object.
        """
        if not self.progress_bar_type:
            self.progress_bar = self._NoProgressBar()
        else:
            self.progress_bar = self.progress_bar_type(
                message, max=maximum, suffix="%(index)d/%(max)d"
            )

        return self

    def __enter__(self):
        """Enter context: return progress bar to allow calling next()."""
        return self.progress_bar

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context: clean up by finish()ing the progress bar."""
        self.progress_bar.finish()


class Stm32Bootloader:
    """Talk to the STM32 native bootloader."""

    # pylint: disable=too-many-public-methods

    class Command:
        """STM32 native bootloader command values."""

        # pylint: disable=too-few-public-methods
        # FIXME turn into intenum   pylint: disable=fixme

        # See ST AN3155, AN4872
        GET = 0x00
        GET_VERSION = 0x01
        GET_ID = 0x02
        READ_MEMORY = 0x11
        GO = 0x21
        WRITE_MEMORY = 0x31
        ERASE = 0x43
        READOUT_PROTECT = 0x82
        READOUT_UNPROTECT = 0x92
        # these not supported on BlueNRG
        EXTENDED_ERASE = 0x44
        WRITE_PROTECT = 0x63
        WRITE_UNPROTECT = 0x73

        # not used so far
        READOUT_PROTECT = 0x82
        READOUT_UNPROTECT = 0x92

        # not really listed under commands, but still...
        # 'wake the bootloader' == 'activate USART' == 'synchronize'
        SYNCHRONIZE = 0x7F

    class Reply:
        """STM32 native bootloader reply status codes."""

        # pylint: disable=too-few-public-methods
        # FIXME turn into intenum   pylint: disable=fixme

        # See ST AN3155, AN4872
        ACK = 0x79
        NACK = 0x1F

    UID_ADDRESS = {
        # No unique id for these parts
        "F0": None,
        # ST RM0008 section 30.1 Unique device ID register
        # F101, F102, F103, F105, F107
        "F1": 0x1FFFF7E8,
        # ST RM0366 section 29.1 Unique device ID register
        # ST RM0365 section 34.1 Unique device ID register
        # ST RM0316 section 34.1 Unique device ID register
        # ST RM0313 section 32.1 Unique device ID register
        # F303/328/358/398, F301/318, F302, F37x
        "F3": 0x1FFFF7AC,
        # ST RM0090 section 39.1 Unique device ID register
        # F405/415, F407/417, F427/437, F429/439
        "F4": 0x1FFF7A10,
        # ST RM0385 section 41.2 Unique device ID register
        "F7": 0x1FF0F420,
        # ST RM0394 47.1 Unique device ID register (96 bits)
        "L4": 0x1FFF7590,
        # ST RM0444 section 38.1 Unique device ID register
        "G0": 0x1FFF7590,
    }

    UID_SWAP = [[1, 0], [3, 2], [7, 6, 5, 4], [11, 10, 9, 8]]

    # Part does not support unique ID feature
    UID_NOT_SUPPORTED = 0
    # stm32loader does not know the address for the unique ID
    UID_ADDRESS_UNKNOWN = -1

    FLASH_SIZE_ADDRESS = {
        # ST RM0360 section 27.1 Memory size data register
        # F030x4/x6/x8/xC, F070x6/xB
        "F0": 0x1FFFF7CC,
        # ST RM0008 section 30.2 Memory size registers
        # F101, F102, F103, F105, F107
        "F1": 0x1FFFF7E0,
        # ST RM0366 section 29.2 Memory size data register
        # ST RM0365 section 34.2 Memory size data register
        # ST RM0316 section 34.2 Memory size data register
        # ST RM0313 section 32.2 Flash memory size data register
        # F303/328/358/398, F301/318, F302, F37x
        "F3": 0x1FFFF7CC,
        # ST RM0090 section 39.2 Flash size
        # F405/415, F407/417, F427/437, F429/439
        "F4": 0x1FFF7A22,
        # ST RM0385 section 41.2 Flash size
        "F7": 0x1FF0F442,
        # ST RM0394
        "L4": 0x1FFF75E0,
        # ST RM0444 section 38.2 Flash memory size data register
        "G0": 0x1FFF75E0,
    }

    DATA_TRANSFER_SIZE = 256  # bytes
    FLASH_PAGE_SIZE = 1024  # bytes

    SYNCHRONIZE_ATTEMPTS = 2

    def __init__(self, connection, verbosity=5, show_progress=None):
        """
        Construct the Stm32Bootloader object.

        The supplied connection can be any object that supports
        read() and write().  Optionally, it may also offer
        enable_reset() and enable_boot0(); it should advertise this by
        setting TOGGLES_RESET and TOGGLES_BOOT0 to True.

        The default implementation is stm32loader.connection.SerialConnection,
        but a straight pyserial serial.Serial object can also be used.

        :param connection: Object supporting read() and write().
          E.g. serial.Serial().
        :param int verbosity: Verbosity level. 0 is quite, 10 is verbose.
        :param ShowProgress show_progress: ShowProgress context manager.
           Set to None to disable progress bar output.
        """
        self.connection = connection
        self.verbosity = verbosity
        self.show_progress = show_progress or ShowProgress(None)
        self.extended_erase = False

    def write(self, *data):
        """Write the given data to the MCU."""
        for data_bytes in data:
            if isinstance(data_bytes, int):
                data_bytes = struct.pack("B", data_bytes)
            self.connection.write(data_bytes)

    def write_and_ack(self, message, *data):
        """Write data to the MCU and wait until it replies with ACK."""
        # this is a separate method from write() because a keyword
        # argument after *args is not possible in Python 2
        self.write(*data)
        return self._wait_for_ack(message)

    def debug(self, level, message):
        """Print the given message if its level is low enough."""
        if self.verbosity >= level:
            Console_output_fn(message)

    def reset_from_system_memory(self):
        """Reset the MCU with boot0 enabled to enter the bootloader."""
        self._enable_boot0(True)
        self._reset()

        # Try the 0x7F synchronize that selects UART in bootloader mode
        # (see ST application notes AN3155 and AN2606).
        # If we are right after reset, it returns ACK, otherwise first
        # time nothing, then NACK.
        # This is not documented in STM32 docs fully, but ST official
        # tools use the same algorithm.
        # This is likely an artifact/side effect of each command being
        # 2-bytes and having xor of bytes equal to 0xFF.

        for attempt in range(self.SYNCHRONIZE_ATTEMPTS):
            if attempt:
                self.debug(5, "Bootloader activation timeout -- retrying")
            self.write(self.Command.SYNCHRONIZE)
            read_data = bytearray(self.connection.read())

            if read_data and read_data[0] in (self.Reply.ACK, self.Reply.NACK):
                # success
                return

        # not successful
        raise CommandError("Bad reply from bootloader")

    def reset_from_flash(self):
        """Reset the MCU with boot0 disabled."""
        self._enable_boot0(False)
        self._reset()

    def command(self, command, description):
        """
        Send the given command to the MCU.

        Raise CommandError if there's no ACK replied.
        """
        self.debug(10, "*** Command: %s" % description)
        ack_received = self.write_and_ack("Command", command, command ^ 0xFF)
        if not ack_received:
            raise CommandError("%s (%s) failed: no ack" % (description, command))

    def get(self):
        """Return the bootloader version and remember supported commands."""
        self.command(self.Command.GET, "Get")
        length = bytearray(self.connection.read())[0]
        version = bytearray(self.connection.read())[0]
        self.debug(10, "    Bootloader version: " + hex(version))
        data = bytearray(self.connection.read(length))
        if self.Command.EXTENDED_ERASE in data:
            self.extended_erase = True
        self.debug(10, "    Available commands: " + ", ".join(hex(b) for b in data))
        self._wait_for_ack("0x00 end")
        return version

    def get_version(self):
        """
        Return the bootloader version.

        Read protection status readout is not yet implemented.
        """
        self.command(self.Command.GET_VERSION, "Get version")
        data = bytearray(self.connection.read(3))
        version = data[0]
        option_byte1 = data[1]
        option_byte2 = data[2]
        self._wait_for_ack("0x01 end")
        self.debug(10, "    Bootloader version: " + hex(version))
        self.debug(10, "    Option byte 1: " + hex(option_byte1))
        self.debug(10, "    Option byte 2: " + hex(option_byte2))
        return version

    def get_id(self):
        """Send the 'Get ID' command and return the device (model) ID."""
        self.command(self.Command.GET_ID, "Get ID")
        length = bytearray(self.connection.read())[0]
        id_data = bytearray(self.connection.read(length + 1))
        self._wait_for_ack("0x02 end")
        _device_id = reduce(lambda x, y: x * 0x100 + y, id_data)
        return _device_id

    def get_flash_size(self, device_family):
        """Return the MCU's flash size in bytes."""
        flash_size_address = self.FLASH_SIZE_ADDRESS[device_family]
        flash_size_bytes = self.read_memory(flash_size_address, 2)
        flash_size = flash_size_bytes[0] + (flash_size_bytes[1] << 8)
        return flash_size

    def get_flash_size_and_uid_f4(self):
        """
        Return device_uid and flash_size for F4 family.

        For some reason, F4 (at least, NUCLEO F401RE) can't read the 12 or 2
        bytes for UID and flash size directly.
        Reading a whole chunk of 256 bytes at 0x1FFFA700 does work and
        requires some data extraction.
        """
        data_start_addr = 0x1FFF7A00
        flash_size_lsb_addr = 0x22
        uid_lsb_addr = 0x10
        data = self.read_memory(data_start_addr, self.DATA_TRANSFER_SIZE)
        device_uid = data[uid_lsb_addr : uid_lsb_addr + 12]
        flash_size = data[flash_size_lsb_addr] + data[flash_size_lsb_addr + 1] << 8
        return flash_size, device_uid

    def get_uid(self, deviceId):
        """
        Send the 'Get UID' command and return the device UID.

        Return UID_NOT_SUPPORTED if the device does not have
        a UID.
        Return UIT_ADDRESS_UNKNOWN if the address of the device's
        UID is not known.

        :param str deviceId: Device family name such as "F1".
          See UID_ADDRESS.
        :return byterary: UID bytes of the device, or 0 or -1 when
          not available.
        """
        uid_address = self.UID_ADDRESS.get(deviceId, self.UID_ADDRESS_UNKNOWN)
        if uid_address is None:
            return self.UID_NOT_SUPPORTED
        if uid_address == self.UID_ADDRESS_UNKNOWN:
            return self.UID_ADDRESS_UNKNOWN

        uid = self.read_memory(uid_address, 12)
        return uid

    @classmethod
    def format_uid(cls, uid):
        """Return a readable string from the given UID."""
        if uid == cls.UID_NOT_SUPPORTED:
            return "UID not supported in this part"
        if uid == cls.UID_ADDRESS_UNKNOWN:
            return "UID address unknown"

        swapped_data = [[uid[b] for b in part] for part in Stm32Bootloader.UID_SWAP]
        uid_string = "-".join("".join(format(b, "02X") for b in part) for part in swapped_data)
        return uid_string

    def read_memory(self, address, length):
        """
        Return the memory contents of flash at the given address.

        Supports maximum 256 bytes.
        """
        if length > self.DATA_TRANSFER_SIZE:
            raise DataLengthError("Can not read more than 256 bytes at once.")
        self.command(self.Command.READ_MEMORY, "Read memory")
        self.write_and_ack("0x11 address failed", self._encode_address(address))
        nr_of_bytes = (length - 1) & 0xFF
        checksum = nr_of_bytes ^ 0xFF
        self.write_and_ack("0x11 length failed", nr_of_bytes, checksum)
        return bytearray(self.connection.read(length))

    def go(self, address):
        """Send the 'Go' command to start execution of firmware."""
        # pylint: disable=invalid-name
        self.command(self.Command.GO, "Go")
        self.write_and_ack("0x21 go failed", self._encode_address(address))

    def write_memory(self, address, data):
        """
        Write the given data to flash at the given address.

        Supports maximum 256 bytes.
        """
        nr_of_bytes = len(data)
        if nr_of_bytes == 0:
            return
        if nr_of_bytes > self.DATA_TRANSFER_SIZE:
            raise DataLengthError("Can not write more than 256 bytes at once.")
        self.command(self.Command.WRITE_MEMORY, "Write memory")
        self.write_and_ack("0x31 address failed", self._encode_address(address))

        # pad data length to multiple of 4 bytes
        if nr_of_bytes % 4 != 0:
            padding_bytes = 4 - (nr_of_bytes % 4)
            nr_of_bytes += padding_bytes
            # append value 0xFF: flash memory value after erase
            data = bytearray(data)
            data.extend([0xFF] * padding_bytes)

        self.debug(10, "    %s bytes to write" % [nr_of_bytes])
        checksum = reduce(operator.xor, data, nr_of_bytes - 1)
        self.write_and_ack("0x31 programming failed", nr_of_bytes - 1, data, checksum)
        self.debug(10, "    Write memory done")

    def erase_memory(self, pages=None):
        """
        Erase flash memory at the given pages.

        Set pages to None to erase the full memory.
        :param iterable pages: Iterable of integer page addresses, zero-based.
          Set to None to trigger global mass erase.
        """
        if self.extended_erase:
            # use erase with two-byte addresses
            self.extended_erase_memory(pages)
            return

        self.command(self.Command.ERASE, "Erase memory")
        if pages:
            # page erase, see ST AN3155
            if len(pages) > 255:
                raise PageIndexError(
                    "Can not erase more than 255 pages at once.\n"
                    "Set pages to None to do global erase or supply fewer pages."
                )
            page_count = (len(pages) - 1) & 0xFF
            page_numbers = bytearray(pages)
            checksum = reduce(operator.xor, page_numbers, page_count)
            self.write(page_count, page_numbers, checksum)
        else:
            # global erase: n=255 (page count)
            self.write(255, 0)

        self._wait_for_ack("0x43 erase failed")
        self.debug(10, "    Erase memory done")

    def extended_erase_memory(self, pages=None):
        """
        Erase flash memory using two-byte addressing at the given pages.

        Set pages to None to erase the full memory.

        Not all devices support the extended erase command.

        :param iterable pages: Iterable of integer page addresses, zero-based.
          Set to None to trigger global mass erase.
        """
        self.command(self.Command.EXTENDED_ERASE, "Extended erase memory")
        if pages:
            # page erase, see ST AN3155
            if len(pages) > 65535:
                raise PageIndexError(
                    "Can not erase more than 65535 pages at once.\n"
                    "Set pages to None to do global erase or supply fewer pages."
                )
            page_count = (len(pages) & 0xFF) - 1
            page_count_bytes = bytearray(struct.pack(">H", page_count))
            page_bytes = bytearray(len(pages) * 2)
            for i, page in enumerate(pages):
                struct.pack_into(">H", page_bytes, i * 2, page)
            checksum = reduce(operator.xor, page_count_bytes)
            checksum = reduce(operator.xor, page_bytes, checksum)
            self.write(page_count_bytes, page_bytes, checksum)
        else:
            # global mass erase: n=0xffff (page count) + checksum
            # TO DO: support 0xfffe bank 1 erase / 0xfffe bank 2 erase
            self.write(b"\xff\xff\x00")

        previous_timeout_value = self.connection.timeout
        self.connection.timeout = 30
        self.debug(5, "Extended erase (0x44), this can take ten seconds or more")
        try:
            self._wait_for_ack("0x44 erasing failed")
        finally:
            self.connection.timeout = previous_timeout_value
        self.debug(10, "    Extended Erase memory done")

    def write_protect(self, pages):
        """Enable write protection on the given flash pages."""
        self.command(self.Command.WRITE_PROTECT, "Write protect")
        nr_of_pages = (len(pages) - 1) & 0xFF
        page_numbers = bytearray(pages)
        checksum = reduce(operator.xor, page_numbers, nr_of_pages)
        self.write_and_ack("0x63 write protect failed", nr_of_pages, page_numbers, checksum)
        self.debug(10, "    Write protect done")

    def write_unprotect(self):
        """Disable write protection of the flash memory."""
        self.command(self.Command.WRITE_UNPROTECT, "Write unprotect")
        self._wait_for_ack("0x73 write unprotect failed")
        self.debug(10, "    Write Unprotect done")

    def readout_protect(self):
        """Enable readout protection of the flash memory."""
        self.command(self.Command.READOUT_PROTECT, "Readout protect")
        self._wait_for_ack("0x82 readout protect failed")
        self.debug(10, "    Read protect done")

    def readout_unprotect(self):
        """
        Disable readout protection of the flash memory.

        Beware, this will erase the flash content.
        """
        self.command(self.Command.READOUT_UNPROTECT, "Readout unprotect")
        self._wait_for_ack("0x92 readout unprotect failed")
        self.debug(20, "    Mass erase -- this may take a while")
        time.sleep(20)
        self.debug(20, "    Unprotect / mass erase done")
        self.debug(20, "    Reset after automatic chip reset due to readout unprotect")
        self.reset_from_system_memory()

    def read_memory_data(self, address, length):
        """
        Return flash content from the given address and byte count.

        Length may be more than 256 bytes.
        """
        data = bytearray()
        chunk_count = int(math.ceil(length / float(self.DATA_TRANSFER_SIZE)))
        self.debug(5, "Read %d chunks at address 0x%X..." % (chunk_count, address))
        with self.show_progress("Reading", maximum=chunk_count) as progress_bar:
            while length:
                read_length = min(length, self.DATA_TRANSFER_SIZE)
                self.debug(
                    10,
                    "Read %(len)d bytes at 0x%(address)X"
                    % {"address": address, "len": read_length},
                )
                data = data + self.read_memory(address, read_length)
                progress_bar.next()
                length = length - read_length
                address = address + read_length
        return data

    def write_memory_data(self, address, data):
        """
        Write the given data to flash.

        Data length may be more than 256 bytes.
        """
        length = len(data)
        chunk_count = int(math.ceil(length / float(self.DATA_TRANSFER_SIZE)))
        offset = 0
        self.debug(5, "Write %d chunks at address 0x%X..." % (chunk_count, address))

        with self.show_progress("Writing", maximum=chunk_count) as progress_bar:
            while length:
                write_length = min(length, self.DATA_TRANSFER_SIZE)
                self.debug(
                    10,
                    "Write %(len)d bytes at 0x%(address)X"
                    % {"address": address, "len": write_length},
                )
                self.write_memory(address, data[offset : offset + write_length])
                progress_bar.next()
                length -= write_length
                offset += write_length
                address += write_length

    @staticmethod
    def verify_data(read_data, reference_data):
        """
        Raise an error if the given data does not match its reference.

        Error type is DataMismatchError.

        :param read_data: Data to compare.
        :param reference_data: Data to compare, as reference.
        :return None:
        """
        if read_data == reference_data:
            return

        if len(read_data) != len(reference_data):
            raise DataMismatchError(
                "Data length does not match: %d bytes vs %d bytes."
                % (len(read_data), len(reference_data))
            )

        # data differs; find out where and raise VerifyError
        for address, data_pair in enumerate(zip(reference_data, read_data)):
            reference_byte, read_byte = data_pair
            if reference_byte != read_byte:
                raise DataMismatchError(
                    "Verification data does not match read data. "
                    "First mismatch at address: 0x%X read 0x%X vs 0x%X expected."
                    % (address, bytearray([read_byte])[0], bytearray([reference_byte])[0])
                )

    def _reset(self):
        """Enable or disable the reset IO line (if possible)."""
        if not hasattr(self.connection, "enable_reset"):
            return
        self.connection.enable_reset(True)
        time.sleep(0.1)
        self.connection.enable_reset(False)
        time.sleep(0.5)

    def _enable_boot0(self, enable=True):
        """Enable or disable the boot0 IO line (if possible)."""
        if not hasattr(self.connection, "enable_boot0"):
            return

        self.connection.enable_boot0(enable)

    def _wait_for_ack(self, info=""):
        """Read a byte and raise CommandError if it's not ACK."""
        read_data = bytearray(self.connection.read())
        if not read_data:
            raise CommandError("Can't read port or timeout")
        reply = read_data[0]
        if reply == self.Reply.NACK:
            raise CommandError("NACK " + info)
        if reply != self.Reply.ACK:
            raise CommandError("Unknown response. " + info + ": " + hex(reply))

        return 1

    @staticmethod
    def _encode_address(address):
        """Return the given address as big-endian bytes with a checksum."""
        # address in four bytes, big-endian
        address_bytes = bytearray(struct.pack(">I", address))
        # checksum as single byte
        checksum_byte = struct.pack("B", reduce(operator.xor, address_bytes))
        return address_bytes + checksum_byte

#=================================================================================#

# Above code is from "stm32loader-0.5.1/stm32loader/bootloader.py"

import serial
import requests

DEF_SERIAL_PORT = "/dev/serial0"
DEF_BINSRC_STR = "http://www.rotorhazard.com/fw/dev/current/RH_S32_BPill_node.bin"
MAX_SRC_FILE_SIZE = 999999

GPIO_RESET_PIN = 17
GPIO_BOOT0_PIN = 27

# set function to use for console/log output
def set_console_output_fn(conOutFn):
    global Console_output_fn
    if conOutFn:
        Console_output_fn = conOutFn
    else:
        Console_output_fn = print

# returns True if host system detected as Raspberry Pi
def is_sys_raspberry_pi():
    try:
        modelStr = None
        try:
            fileHnd = open("/proc/device-tree/model", "r")
            modelStr = fileHnd.read()
            fileHnd.close()
        except:
            pass
        if modelStr and "raspberry pi" in modelStr.lower():
            return True
    except Exception as ex:
        Console_output_fn("Error in 'is_sys_raspberry_pi()': " + str(ex))
    return False

# reset BPill processor into bootloader mode
def reset_to_boot_0():
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(GPIO_RESET_PIN, GPIO.OUT)
        GPIO.output(GPIO_RESET_PIN, GPIO.HIGH)  # reset pin high (inactive)
        GPIO.setup(GPIO_BOOT0_PIN, GPIO.OUT)
        GPIO.output(GPIO_BOOT0_PIN, GPIO.HIGH)  # boot0 pin high (active)
        time.sleep(0.01)
        GPIO.output(GPIO_RESET_PIN, GPIO.LOW)   # reset pin low (active)
        time.sleep(0.05)
        GPIO.output(GPIO_RESET_PIN, GPIO.HIGH)  # reset pin high (inactive)
        time.sleep(0.1)
        GPIO.output(GPIO_BOOT0_PIN, GPIO.LOW)   # boot0 pin low (inactive)
        GPIO.setup(GPIO_RESET_PIN, GPIO.IN)
        GPIO.setup(GPIO_BOOT0_PIN, GPIO.IN)
    except ImportError as ex:
        Console_output_fn("ImportError in 'reset_to_boot_0()': " + str(ex))
    except Exception as ex:
        Console_output_fn("Error in 'reset_to_boot_0()': " + str(ex))

# reset BPill processor
def reset_to_run():
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(GPIO_RESET_PIN, GPIO.OUT)
        GPIO.output(GPIO_RESET_PIN, GPIO.HIGH)  # reset pin high (inactive)
        time.sleep(0.01)
        GPIO.output(GPIO_RESET_PIN, GPIO.LOW)   # reset pin low (active)
        time.sleep(0.05)
        GPIO.output(GPIO_RESET_PIN, GPIO.HIGH)  # reset pin high (inactive)
        time.sleep(0.1)
        GPIO.setup(GPIO_RESET_PIN, GPIO.IN)
    except ImportError as ex:
        Console_output_fn("ImportError in 'reset_to_run()': " + str(ex))
    except Exception as ex:
        Console_output_fn("Error in 'reset_to_run()': " + str(ex))

# download given URL to buffer
def download_to_buffer(src_url, log_flag=True):
    if log_flag:
        Console_output_fn("Downloading file data from: {}".format(src_url))
    resp = requests.get(src_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:87.0) Gecko/20100101 Firefox/87.0"}, verify=False)
    if resp.status_code != 200:
        raise RuntimeError("Error reading file data, HTTP status code: {}".format(resp.status_code))
    file_size = int(resp.headers["Content-Length"])
    if file_size <= 0:
        raise RuntimeError("File data size is zero")
    if file_size > MAX_SRC_FILE_SIZE:
        raise RuntimeError("File data size too large ({})".format(file_size))
    if log_flag:
        Console_output_fn("Downloaded {} bytes".format(file_size))
    return resp.content

# read given local file to buffer
def read_file_to_buffer(file_str, log_flag=True):
    with open(file_str, "rb") as file_obj:
        file_obj.seek(0,2)  # seek to end of file
        file_size = file_obj.tell()
        if file_size <= 0:
            raise RuntimeError("File data size is zero")
        if file_size > MAX_SRC_FILE_SIZE:
            raise RuntimeError("File data size too large ({})".format(file_size))
        file_obj.seek(0,0)  # seek back to start of file
        if log_flag:
            Console_output_fn("Reading {} bytes from: {}".format(file_size, file_str))
        return file_obj.read()

# read given source file (URL or local) to buffer
def load_source_file(src_str, log_flag=True):
    if src_str.startswith("http://") or src_str.startswith("https://") or src_str.startswith("ftp://"):
        return download_to_buffer(src_str, log_flag)
    else:
        return read_file_to_buffer(src_str, log_flag)

# flash firmware to BPill at given port with data from given file/URL
def flash_file_to_stm32(portStr, srcStr):
    try:
        if not portStr:
            portStr = DEF_SERIAL_PORT
        if not srcStr:
            srcStr = DEF_BINSRC_STR

        binaryData = None
        try:
            if len(srcStr) > 0:
                binaryData = bytearray(load_source_file(srcStr))
        except IOError as ex:
            Console_output_fn("Error loading file from '{}': {}".format(srcStr, ex))
            return False
        
        verboseFlag = False
        memoryAddress = 0x08000000
        goAddress = 0x08000000
        
        isRPiFlag = is_sys_raspberry_pi()
        
        Console_output_fn("stm32loader using port %s" % portStr)
        try:
            serialObj = serial.Serial(port=None, baudrate=57600, parity=serial.PARITY_EVEN, timeout=3, \
                                      rtscts=False, dsrdtr=False)
            serialObj.setDTR(0)  # clear in case line is tied to node-processor reset
            serialObj.setRTS(0)
            serialObj.setPort(portStr)
            serialObj.open()  # open port (now that DTR is configured for no change)
        except IOError as ex:
            Console_output_fn(("Error opening serial port: " + str(ex)))
            return False
        
        bootloaderObj = Stm32Bootloader(serialObj, verbosity=5)
        
        gpioResetFlag = False
        if isRPiFlag:
            bootloaderObj.SYNCHRONIZE_ATTEMPTS = 1
            # first try to see if processor already in bootloader mode
            try:
                bootloaderObj.reset_from_system_memory()
                Console_output_fn("Activated bootloader")
            except CommandError:
                gpioResetFlag = True
            if gpioResetFlag:
                # try to reset into bootloader mode via RPi GPIO outputs
                bootloaderObj.SYNCHRONIZE_ATTEMPTS = 2
                Console_output_fn("Resetting BPill with Boot0 via GPIO")
                reset_to_boot_0()
                try:
                    Console_output_fn("Activating bootloader")
                    bootloaderObj.reset_from_system_memory()
                except CommandError:
                    Console_output_fn("Can't init into bootloader - ensure that Boot0 jumper is installed and RH server is not running")
                    Console_output_fn("Resetting BPill via GPIO")
                    reset_to_run()
                    return False
        else:
            try:
                Console_output_fn("Activating bootloader")
                bootloaderObj.reset_from_system_memory()
            except CommandError:
                Console_output_fn("Can't init into bootloader - ensure that Boot0 is enabled and reset the device")
                bootloaderObj.reset_from_flash()
                return False
    
        successFlag = False
        try:
            bootVersion = bootloaderObj.get()
            Console_output_fn("Device bootloader version: 0x%X" % bootVersion)
            deviceId = bootloaderObj.get_id()
            Console_output_fn("Device chip id: 0x%X (%s)" % (deviceId, CHIP_IDS.get(deviceId, "Unknown")))
            successFlag = True
            family = "F4" if deviceId == 0x431 or deviceId == 0x433 or \
                     deviceId == 0x413 or deviceId == 0x419 else "F1"
            try:
                if family != "F4":
                    flash_size = bootloaderObj.get_flash_size(family)
                    device_uid = bootloaderObj.get_uid(family)
                else:
                    flash_size, device_uid = bootloaderObj.get_flash_size_and_uid_f4()
                device_uid_string = bootloaderObj.format_uid(device_uid)
                Console_output_fn("Device UID: %s" % device_uid_string)
                Console_output_fn("Flash size: %d KiB" % flash_size)
            except CommandError as e:
                Console_output_fn("Error reading chip family data: " + str(e))
            
        except Exception as ex:
            Console_output_fn("Unable to communicate with device: %s" % ex)
    
        if successFlag:
            if verboseFlag:
                bootloaderObj.verbosity = 10
            
            Console_output_fn("Erasing memory")
            bootloaderObj.erase_memory()
    
            if binaryData:
                bootloaderObj.write_memory_data(memoryAddress, binaryData)
                read_data = bootloaderObj.read_memory_data(memoryAddress, len(binaryData))
                try:
                    Stm32Bootloader.verify_data(read_data, binaryData)
                    Console_output_fn("Verification OK")
                except DataMismatchError as e:
                    successFlag = False
                    Console_output_fn("Verification FAILED: %s" % e, file=sys.stdout)
                if successFlag and goAddress >= 0:
                    bootloaderObj.go(goAddress)
            else:
                Console_output_fn("Source file is empty; device firmware erased")
    
        serialObj.close()
    
        if gpioResetFlag:
            Console_output_fn("Resetting BPill via GPIO")
            reset_to_run()
    
        return successFlag

    except Exception as ex:
        Console_output_fn("Error in stm32loader 'flash_file_to_stm32()': " + str(ex))
        traceback.print_exc()
        return False


if __name__ == '__main__':
    argPortStr = sys.argv[1] if len(sys.argv) > 1 else None
    argSrcStr = sys.argv[2] if len(sys.argv) > 2 else None
    flashSuccessFlag = flash_file_to_stm32(argPortStr, argSrcStr)
    sys.exit(0 if flashSuccessFlag else 1)
