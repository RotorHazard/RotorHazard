'''LapRF hardware interface helpers.'''

from struct import pack_into, unpack_from
from enum import IntEnum
from typing import Optional, Union, List
from time import perf_counter_ns
import logging

logger = logging.getLogger(__name__)


SOR = 0x5a
EOR = 0x5b
ESC = 0x5c
ESC_OFFSET = 0x40
MAX_RECORD_LEN = 1024
MAX_SLOTS = 8
MAX_CHANNELS = 8
MAX_THRESHOLD = 3000
MAX_GAIN = 63

LIVE_TIME_BANDS = ['F','R', 'E', 'B', 'A', 'L']


class RecordType(IntEnum):
    RSSI = 0xda01
    RF_SETUP = 0xda02
    STATE_CONTROL = 0xda04
    SETTINGS = 0xda07
    DESCRIPTOR = 0xda08
    PASSING = 0xda09
    STATUS = 0xda0a
    TIME = 0xda0c
    ERROR = 0xffff


class RFSetupField(IntEnum):
    SLOT_INDEX = 0x01
    ENABLED = 0x20
    CHANNEL = 0x21
    BAND = 0x22
    THRESHOLD = 0x23
    GAIN = 0x24
    FREQUENCY = 0x25


class RssiField(IntEnum):
    SLOT_INDEX = 0x01  # uint8
    SAMPLE_COUNT = 0x07  # uint32
    MIN_RSSI = 0x20  # f32
    MAX_RSSI = 0x21  # f32
    MEAN_RSSI = 0x22  # f32
    UNKNOWN_1 = 0x23
    CUSTOM_RATE = 0x24
    PACKET_RATE = 0x25
    UNKNOWN_2 = 0x26


class PassingField(IntEnum):
    SLOT_INDEX = 0x01
    RTC_TIME = 0x02
    DECODER_ID = 0x20
    PASSING_NUMBER = 0x21
    PEAK_HEIGHT = 0x22
    FLAGS = 0x23


class SettingsField(IntEnum):
    STATUS_INTERVAL = 0x22
    SAVE_SETTINGS = 0x25
    MIN_LAP_TIME = 0x26


class StateControlField(IntEnum):
    GATE_STATE = 0x20


class StatusField(IntEnum):
    SLOT_INDEX = 0x01
    FLAGS = 0x03
    BATTERY_VOLTAGE = 0x21
    LAST_RSSI = 0x22
    GATE_STATE = 0x23
    DETECTION_COUNT = 0x24


class TimeField(IntEnum):
    RTC_TIME = 0x02
    TIME_RTC_TIME = 0x20


class LapRFEvent():
    def __init__(self: "LapRFEvent", rec_type: str):
        self.timestamp: int = round(perf_counter_ns()/1000000)
        self.rec_type = rec_type


class RFSetupEvent(LapRFEvent):
    "A LapRF receiver radio frequency setup event"

    def __init__(self: "RFSetupEvent"):
        super().__init__("slot_config")
        self.slot_index: Optional[int] = None
        self.enabled: Optional[bool] = None
        self.band: Optional[int] = None
        self.channel: Optional[int] = None
        self.frequency: Optional[int] = None
        self.threshold: Optional[float] = None
        self.gain: Optional[int] = None

    def is_valid(self: "RFSetupEvent") -> bool:
        return (isinstance(self.slot_index, int) and
                isinstance(self.enabled, bool) and
                isinstance(self.band, int) and
                isinstance(self.channel, int) and
                isinstance(self.frequency, int) and
                isinstance(self.threshold, float) and
                isinstance(self.gain, int))


class PassingEvent(LapRFEvent):
    "A LapRF passing event"

    def __init__(self: "PassingEvent"):
        super().__init__("passing")
        self.slot_index: Optional[int] = None
        self.rtc_time: Optional[int] = None
        self.decoder_id: Optional[int] = None
        self.passing_number: Optional[int] = None
        self.peak_height: Optional[int] = None
        self.flags: Optional[int] = None

    def is_valid(self: "PassingEvent") -> bool:
        return (isinstance(self.slot_index, int) and
                isinstance(self.rtc_time, int) and
                isinstance(self.decoder_id, int) and
                isinstance(self.passing_number, int) and
                isinstance(self.peak_height, int) and
                isinstance(self.flags, int))


# Haven't encounter this type of record.
class RSSIEvent(LapRFEvent):
    "A LapRF RSSI event"

    def __init__(self: "RSSIEvent"):
        super().__init__("rssi")
        self.slot_index: Optional[int] = None
        self.min_rssi: Optional[float] = None
        self.max_rssi: Optional[float] = None
        self.mean_rssi: Optional[float] = None

    def is_valid(self: "RSSIEvent") -> bool:
        return (isinstance(self.slot_index, int) and
                isinstance(self.min_rssi, float) and
                isinstance(self.max_rssi, float) and
                isinstance(self.mean_rssi, float))


class SettingsEvent(LapRFEvent):
    "A LapRF settings event"

    def __init__(self: "SettingsEvent"):
        super().__init__("settings")
        self.status_interval: Optional[int] = None
        self.min_lap_time: Optional[int] = None

    def is_valid(self: "SettingsEvent") -> bool:
        if self.status_interval and not isinstance(self.status_interval, int):
            return False
        if self.min_lap_time and not isinstance(self.min_lap_time, int):
            return False
        return True


class StatusEvent(LapRFEvent):
    "A LapRF status event"

    def __init__(self: "StatusEvent"):
        super().__init__("status")
        self.battery_voltage: Optional[int] = None
        self.gate_state: Optional[int] = None
        self.detection_count: Optional[int] = None
        self.flags: Optional[int] = None
        self.last_rssi: List[Optional[float]] = [None] * MAX_SLOTS

    def is_valid(self: "StatusEvent") -> bool:
        for slot in self.last_rssi:
            if not isinstance(slot, float):
                return False
        return (isinstance(self.battery_voltage, int) and
                isinstance(self.gate_state, int) and
                isinstance(self.detection_count, int) and
                isinstance(self.flags, int))


class TimeEvent(LapRFEvent):
    "A LapRF time event"

    def __init__(self: "TimeEvent"):
        super().__init__("time")
        self.rtc_time: Optional[int] = None
        self.time_rtc_time: Optional[int] = None

    def is_valid(self: "TimeEvent") -> bool:
        return (isinstance(self.rtc_time, int) and
                isinstance(self.time_rtc_time, int))


Event = Union[RFSetupEvent, PassingEvent, SettingsEvent, StatusEvent, TimeEvent]


class InvalidRecordError(Exception):
    """Exception raised for an invalid LapRF record.
    """

    def __init__(self, message="Invalid LapRF record"):
        self.message = message
        super().__init__(self.message)


class CrcMismatchError(Exception):
    """Exception raised for a CRC mismatch.
    """

    def __init__(self, message="LapRF record CRC mismatch"):
        self.message = message
        super().__init__(self.message)


class ByteSizeError(Exception):
    """Exception raised for a byte size mismatch.
    """

    def __init__(self, expected: int, received: int):
        self.message = f"Byte size mismatch expected: {expected}, received: {received}"
        super().__init__(self.message)


def _escape_record(input_data: bytearray) -> bytes:
    """Escape a LapRF record.
    """
    output = []
    byte: int
    length = len(input_data)
    last_index = length - 1
    for offset in range(length):
        byte = input_data[offset]
        if (byte == ESC or byte == SOR or byte == EOR) and offset != 0 and offset != last_index:
            output.append(ESC)
            output.append(byte + ESC_OFFSET)
        else:
            output.append(byte)
    return bytes(output)


def _unescape_record(input_data: bytes) -> bytearray:
    """Unescape a LapRF record.
    """
    output = []
    byte: int
    escaped = False
    for offset in range(len(input_data)):
        byte = input_data[offset]
        if escaped:
            escaped = False
            output.append(byte - ESC_OFFSET)
        else:
            if byte == EOR:
                output.append(byte)
                return bytearray(output)
            elif byte == ESC:
                escaped = True
            else:
                output.append(byte)
    raise InvalidRecordError("Record unescape failed")


def _split_records(input_data: bytes) -> List[bytearray]:
    """Split a LapRF packet into individual unescaped records.
    """
    output = []
    pos = 0
    while True:
        sor = input_data.find(SOR, pos)
        if (sor > -1):
            pos = input_data.find(EOR, sor)
            if (pos > -1):
                output.append(_unescape_record(input_data[sor:pos+1]))
            else:
                break
        else:
            break
    return output


def _gen_crc_16_table():
    table = []
    remainder = 0
    for x in range(256):
        remainder = (x << 8) & 0xff00
        for _ in range(8):
            if remainder & 0x8000 == 0x8000:
                remainder = ((remainder << 1) & 0xffff) ^ 0x8005
            else:
                remainder = (remainder << 1) & 0xffff
        table.append(remainder)
    return table


def _reflect(input_data: int, nbits: int) -> int:
    shift = input_data
    output = 0
    for x in range(nbits):
        if (shift & 0x01) == 0x01:
            output |= 1 << (nbits - 1 - x)
        shift >>= 1
    return output


def _compute(buffer: bytes) -> int:
    remainder = 0
    for offset in range(len(buffer)):
        a = _reflect(buffer[offset], 8)
        a &= 0xff
        b = (remainder >> 8) & 0xff
        c = (remainder << 8) & 0xffff
        data = a ^ b
        remainder = crc_16_table[data] ^ c
    return _reflect(remainder, 16)


def _verify_crc(buffer: bytes) -> None:
    """Verify a LapRF record by performing a cyclic redundancy check (CRC).

    WARNING: The `buffer` is modified in order to verify the CRC. Its required to remove
    the CRC field from the record, because it was not in the record when it was generated.

    Args:
        buffer: A LapRF record to verify.

    Returns:
      None

    Raises:
      CrcError: An error of a CRC mismatch.
    """
    crc_record, = unpack_from("<H", buffer, 3)
    buffer_no_crc = bytearray(buffer)
    pack_into("<H", buffer_no_crc, 3, 0)
    crc_computed = _compute(buffer_no_crc)
    if (crc_record != crc_computed):
        raise CrcMismatchError()


crc_16_table = _gen_crc_16_table()


class Encoder:
    """A LapRF record decoder.

    Attributes:
      pos: An integer cursor postion in the buffer.
      type: An interger representing the type of record.
    """

    def __init__(self, rec_type: int):
        self.pos = 7
        self.rec_type = rec_type
        self._buffer = bytearray(MAX_RECORD_LEN)
        # Start LapRF Record
        pack_into(
            "<BHHH",  # 7 bytes
            self._buffer,
            0,
            SOR,
            0,  # byte length
            0,  # CRC
            rec_type
        )

    def finish(self: "Encoder") -> bytes:
        """Finish LapRF Record

        Returns:
          The complete and escaped LapRF record.
        """
        pack_into("<B", self._buffer, self.pos, EOR)
        self._advance(1)
        record = self._buffer[0:self.pos]
        pack_into("<H", record, 1, self.pos)
        pack_into("<H", record, 3, _compute(record))
        escaped = _escape_record(record)
        return escaped

    def write_u8(self: "Encoder", value: int) -> "Encoder":
        """Write a single byte to the internal buffer
        """
        if value < 0 or value > 255:
            raise Exception('Invalid argument, value must be a 8 bit unsigned integer')
        pack_into("<B", self._buffer, self.pos, value)
        self._advance(1)
        return self

    def encode_u8_field(self: "Encoder", signature: int, value: int) -> "Encoder":
        """Encode an unsigned 8 bit integer field.
        """
        if value < 0 or value > 255:
            raise Exception('Invalid argument, value must be a 8 bit unsigned integer')
        pack_into("<BBB", self._buffer, self.pos, signature, 1, value)
        self._advance(3)  # u8, u8, u8
        return self

    def encode_u16_field(self: "Encoder", signature: int, value: int) -> "Encoder":
        """Encode an unsigned 16 bit integer field.
        """
        if value < 0 or value > 65_535:
            raise Exception('Invalid argument, value must be a 16 bit unsigned integer')
        pack_into("<BBH", self._buffer, self.pos, signature, 2, value)
        self._advance(4)  # u8, u8, u16
        return self

    def encode_u32_field(self: "Encoder", signature: int, value: int) -> "Encoder":
        """Encode an unsigned 32 bit integer field.
        """
        if value < 0 or value > 4_294_967_295:
            raise Exception('Invalid argument, value must be a 32 bit unsigned integer')
        pack_into("<BBI", self._buffer, self.pos, signature, 4, value)
        self._advance(6)  # u8, u8, u32
        return self

    def encode_u64_field(self: "Encoder", signature: int, value: int) -> "Encoder":
        """Encode an unsigned 64 bit integer field.
        """
        pack_into("<BBQ", self._buffer, self.pos, signature, 8, value)
        self._advance(10)  # u8, u8, u64
        return self

    def encode_f32_field(self: "Encoder", signature: int, value: float) -> "Encoder":
        """Encode a 32 bit float field.
        """
        pack_into("<BBf", self._buffer, self.pos, signature, 4, value)
        self._advance(6)  # u8, u8, f32
        return self

    def encode_f64_field(self: "Encoder", signature: int, value: float) -> "Encoder":
        """Encode a 64 bit float field.
        """
        pack_into("<BBd", self._buffer, self.pos, signature, 8, value)
        self._advance(10)  # u8, u8, f64
        return self

    def _advance(self: "Encoder", byte_length: int):
        self.pos += byte_length


class Decoder:
    """A LapRF record decoder.

    Attributes:
      pos: An integer cursor postion in the buffer.
      type: An interger representing the type of record.
      length: An integer byte length of the record.
    """

    def __init__(self, buffer: bytes):
        length, _, rec_type = unpack_from("<HHH", buffer, 1)
        if len(buffer) != length:
            raise InvalidRecordError(f"Invalid record length of {len(buffer)}, expected {length}")
        _verify_crc(buffer)
        self.pos = 7
        self.rec_type: int = rec_type
        self.length: int = length
        self._buffer = buffer

    def decode_field_signature(self: "Decoder") -> int:
        """Decode record field signature.
        """
        signature, = unpack_from("<B", self._buffer, self.pos)
        self.pos += 1
        return signature

    def decode_u8_field(self: "Decoder") -> int:
        """Decode an unsigned byte field.
        """
        size, data = unpack_from("<BB", self._buffer, self.pos)
        self._advance(1, size)
        return data

    def decode_u16_field(self: "Decoder") -> int:
        """Decode an unsigned 16 bit integer field.
        """
        size, data = unpack_from("<BH", self._buffer, self.pos)
        self._advance(2, size)
        return data

    def decode_u32_field(self: "Decoder") -> int:
        """Decode an unsigned 32 bit integer field.
        """
        size, data = unpack_from("<BI", self._buffer, self.pos)
        self._advance(4, size)
        return data

    def decode_u64_field(self: "Decoder") -> int:
        """Decode an unsigned 64 bit integer field.
        """
        size, data = unpack_from("<BQ", self._buffer, self.pos)
        self._advance(8, size)
        return data

    def decode_f32_field(self: "Decoder") -> float:
        """Decode a 32 bit float field.
        """
        size, data = unpack_from("<Bf", self._buffer, self.pos)
        self._advance(4, size)
        return data

    def decode_f64_field(self: "Decoder") -> float:
        """Decode a 64 bit float field.
        """
        size, data = unpack_from("<Bd", self._buffer, self.pos)
        self._advance(8, size)
        return data

    def skip_unknown_field(self: "Decoder", signature: int) -> None:
        """Skip a LapRF record field
        """
        t = hex(self.rec_type)
        s = hex(signature)
        logger.warning(f"Unknown field signature {s} found in record type record type {t}")
        size, = unpack_from("<B", self._buffer, self.pos)
        self.pos += size + 1  # Also skip over the size byte that was read above.

    def _advance(self: "Decoder", expected: int, received: int) -> None:
        if expected == received:
            self.pos += expected + 1  # Also skip over the size byte that was read above.
        else:
            raise ByteSizeError(expected, received)


def _decode_rf_setup_record(record: Decoder) -> RFSetupEvent:
    event = RFSetupEvent()
    while record.pos < record.length:
        signature = record.decode_field_signature()
        if signature == EOR:
            break
        elif signature == RFSetupField.SLOT_INDEX:
            event.slot_index = record.decode_u8_field()
        elif signature == RFSetupField.ENABLED:
            event.enabled = True if record.decode_u16_field() == 1 else False
        elif signature == RFSetupField.BAND:
            event.band = record.decode_u16_field()
        elif signature == RFSetupField.CHANNEL:
            event.channel = record.decode_u16_field()
        elif signature == RFSetupField.BAND:
            event.band = record.decode_u16_field()
        elif signature == RFSetupField.FREQUENCY:
            event.frequency = record.decode_u16_field()
        elif signature == RFSetupField.THRESHOLD:
            event.threshold = record.decode_f32_field()
        elif signature == RFSetupField.GAIN:
            event.gain = record.decode_u16_field()
        else:
            record.skip_unknown_field(signature)
    return event


# def _decode_rssi_record(record: Decoder) -> RSSIEvent:


def _decode_settings_record(record: Decoder) -> SettingsEvent:
    event = SettingsEvent()
    while record.pos < record.length:
        signature = record.decode_field_signature()
        if signature == EOR:
            break
        elif signature == SettingsField.STATUS_INTERVAL:
            event.status_interval = record.decode_u16_field()
        elif signature == SettingsField.SAVE_SETTINGS:
            record.decode_u8_field()  # Discard, should only be used on a request.
        elif signature == SettingsField.MIN_LAP_TIME:
            event.min_lap_time = record.decode_u32_field()
        else:
            record.skip_unknown_field(signature)
    return event


def _decode_passing_record(record: Decoder) -> PassingEvent:
    event = PassingEvent()
    while record.pos < record.length:
        signature = record.decode_field_signature()
        if signature == EOR:
            break
        elif signature == PassingField.SLOT_INDEX:
            event.slot_index = record.decode_u8_field()
        elif signature == PassingField.RTC_TIME:
            event.rtc_time = record.decode_u64_field()
        elif signature == PassingField.DECODER_ID:
            event.decoder_id = record.decode_u32_field()
        elif signature == PassingField.PASSING_NUMBER:
            event.passing_number = record.decode_u32_field()
        elif signature == PassingField.PEAK_HEIGHT:
            event.peak_height = record.decode_u16_field()
        elif signature == PassingField.FLAGS:
            event.flags = record.decode_u16_field()
        else:
            record.skip_unknown_field(signature)
    return event


def _decode_status_record(record: Decoder) -> StatusEvent:
    slot_index: Optional[int] = None
    event = StatusEvent()
    while record.pos < record.length:
        signature = record.decode_field_signature()
        if signature == EOR:
            break
        elif signature == StatusField.SLOT_INDEX:
            slot_index = record.decode_u8_field()
        elif signature == StatusField.FLAGS:
            event.flags = record.decode_u16_field()
        elif signature == StatusField.BATTERY_VOLTAGE:
            event.battery_voltage = record.decode_u16_field()
        elif signature == StatusField.LAST_RSSI:
            if slot_index and slot_index > 0:
                slot_index = slot_index - 1  # convert to 1-based index
                if (slot_index < MAX_SLOTS):
                    event.last_rssi[slot_index] = record.decode_f32_field()
            slot_index = None  # reset for next loop
        elif signature == StatusField.GATE_STATE:
            event.gate_state = record.decode_u8_field()
        elif signature == StatusField.DETECTION_COUNT:
            event.detection_count = record.decode_u32_field()
        else:
            record.skip_unknown_field(signature)
    return event


def _decode_time_record(record: Decoder) -> TimeEvent:
    event = TimeEvent()
    while record.pos < record.length:
        signature = record.decode_field_signature()
        if signature == EOR:
            break
        elif signature == TimeField.RTC_TIME:
            event.rtc_time = record.decode_u64_field()
        elif signature == TimeField.TIME_RTC_TIME:
            # Need to research difference from rtc_time.
            event.time_rtc_time = record.decode_u64_field()
        else:
            record.skip_unknown_field(signature)
    return event


def _decode_record(buffer: bytes):
    record = Decoder(buffer)
    if record.rec_type == RecordType.RF_SETUP:
        return _decode_rf_setup_record(record)
    elif record.rec_type == RecordType.RSSI:
        # _decode_rssi_record(record)
        pass
    elif record.rec_type == RecordType.PASSING:
        return _decode_passing_record(record)
    elif record.rec_type == RecordType.SETTINGS:
        return _decode_settings_record(record)
    elif record.rec_type == RecordType.STATUS:
        return _decode_status_record(record)
    elif record.rec_type == RecordType.TIME:
        return _decode_time_record(record)
    # elif record.rec_type == RecordType.Descriptor:
    # Record Type: 0xda08, Unknown Signature: 0x20, Size: 4
    # Record Type: 0xda08, Unknown Signature: 0x21, Size: 1
    else:
        logger.warning("Unrecognised record type: {:#04x}".format(record.rec_type))


# Module Public Functions


def decode(packet: bytes):
    """Deserialize a LapRF packet.
    """
    records: List[Event] = []
    buffers = _split_records(packet)
    for buffer in buffers:
        try:
            record = _decode_record(buffer)
            if record:
                records.append(record)
        except:
            # TODO - Log errors
            pass
    return records


def encode_get_rtc_time_record() -> bytes:
    """Encode a LapRF RF record to request the RTC time.
    """
    # Requesting the RTC time requires an irregular packet.
    return (Encoder(RecordType.TIME)
            .write_u8(TimeField.RTC_TIME)
            .write_u8(0x00)
            .finish())


def encode_get_min_lap_time_record() -> bytes:
    """Encode a LapRF RF record to get the minimum lap time setting.
    """
    return (Encoder(RecordType.SETTINGS)
            .encode_u32_field(SettingsField.MIN_LAP_TIME, 0x00)
            .finish())


def encode_set_min_lap_time_record(milliseconds: int) -> bytes:
    """Encode a LapRF RF record to set the minimum lap time setting.
    """
    if not milliseconds:
        raise ValueError("Minimum lap-time must be greater than zero")
    return (Encoder(RecordType.SETTINGS)
            .encode_u32_field(SettingsField.MIN_LAP_TIME, milliseconds)
            .finish())


def encode_set_status_interval_record(milliseconds: int) -> bytes:
    """Encode a LapRF RF record to set the status interval setting.
    """
    if not milliseconds:
        raise ValueError("Status interval must be greater than zero")
    return (Encoder(RecordType.SETTINGS)
            .encode_u16_field(SettingsField.STATUS_INTERVAL, milliseconds)
            .finish())


def encode_get_rf_setup_record(slot_index: Optional[int] = None):
    """Encode a LapRF RF record to request a receiver configuration.

    Request either a single slot, or all if no slot_index is provided.
    """
    record = Encoder(RecordType.RF_SETUP)
    if slot_index and slot_index >= 1 and slot_index <= MAX_SLOTS:
        record.encode_u8_field(RFSetupField.SLOT_INDEX, slot_index)
    else:
        for index in range(1, MAX_SLOTS+1):
            record.encode_u8_field(RFSetupField.SLOT_INDEX, index)
    return record.finish()


def encode_set_rf_setup_record(slot_index: int,  enabled: bool, band: int, channel: int, frequency: int, gain: int, threshold: float) -> bytes:
    """Encode a LapRF RF record to configure a receiver slot

    *NOTE* slot_index, band, and channel all use 1-based indexing

    Attributes:
      slot_index: integer - The slot index to configure.
      band: integer - Radio band. Band order = FREBAL
      channel: integer - Radio channel.
      frequency: integer - Radio frequency.
      gain: integer - The receiver gain.
      threshold: float - The passing threshold.
      enabled: boolean
    """
    return (Encoder(RecordType.RF_SETUP)
            .encode_u8_field(RFSetupField.SLOT_INDEX, slot_index)
            .encode_u16_field(RFSetupField.ENABLED, 1 if enabled else 0)
            .encode_u16_field(RFSetupField.CHANNEL, channel)
            .encode_u16_field(RFSetupField.BAND, band)
            .encode_f32_field(RFSetupField.THRESHOLD, threshold)
            .encode_u16_field(RFSetupField.GAIN, gain)
            .encode_u16_field(RFSetupField.FREQUENCY, frequency)
            .finish())
