import unittest
from interface.laprf_protocol import SOR, EOR, ESC, ESC_OFFSET
import interface.laprf_protocol as protocol


mock_data = {
    "crc": {
        "table": [0, 32773, 32783, 10, 32795, 30, 20, 32785, 32819, 54, 60, 32825, 40, 32813, 32807, 34, 32867, 102, 108, 32873, 120, 32893, 32887, 114, 80, 32853, 32863, 90, 32843, 78, 68, 32833, 32963, 198, 204, 32969, 216, 32989, 32983, 210, 240, 33013, 33023, 250, 33003, 238, 228, 32993, 160, 32933, 32943, 170, 32955, 190, 180, 32945, 32915, 150, 156, 32921, 136, 32909, 32903, 130, 33155, 390, 396, 33161, 408, 33181, 33175, 402, 432, 33205, 33215, 442, 33195, 430, 420, 33185, 480, 33253, 33263, 490, 33275, 510, 500, 33265, 33235, 470, 476, 33241, 456, 33229, 33223, 450, 320, 33093, 33103, 330, 33115, 350, 340, 33105, 33139, 374, 380, 33145, 360, 33133, 33127, 354, 33059, 294, 300, 33065, 312, 33085, 33079, 306, 272, 33045, 33055, 282, 33035, 270, 260, 33025, 33539, 774, 780, 33545, 792, 33565, 33559, 786, 816, 33589, 33599, 826, 33579, 814, 804, 33569, 864, 33637, 33647, 874, 33659, 894, 884, 33649, 33619, 854, 860, 33625, 840, 33613, 33607, 834, 960, 33733, 33743, 970, 33755, 990, 980, 33745, 33779, 1014, 1020, 33785, 1000, 33773, 33767, 994, 33699, 934, 940, 33705, 952, 33725, 33719, 946, 912, 33685, 33695, 922, 33675, 910, 900, 33665, 640, 33413, 33423, 650, 33435, 670, 660, 33425, 33459, 694, 700, 33465, 680, 33453, 33447, 674, 33507, 742, 748, 33513, 760, 33533, 33527, 754, 720, 33493, 33503, 730, 33483, 718, 708, 33473, 33347, 582, 588, 33353, 600, 33373, 33367, 594, 624, 33397, 33407, 634, 33387, 622, 612, 33377, 544, 33317, 33327, 554, 33339, 574, 564, 33329, 33299, 534, 540, 33305, 520, 33293, 33287, 514],
        # Same as tx.set_rf_setup_single but without the CRC value set.
        "record_with_no_crc": bytes([0x5a, 0x25, 0x00, 0x00, 0x00, 0x02, 0xda, 0x01, 0x01, 0x01, 0x20, 0x02, 0x01, 0x00, 0x21, 0x02, 0x02, 0x00, 0x22, 0x02, 0x03, 0x00, 0x23, 0x04, 0x00, 0x00, 0x61, 0x44, 0x24, 0x02, 0x33, 0x00, 0x25, 0x02, 0x35, 0x16, 0x5b]),
    },
    "rx": {
        "rf_setup_record_single": bytes([0x5a, 0x25, 0x00, 0x06, 0x5d, 0x02, 0xda, 0x01, 0x01, 0x01, 0x20, 0x02, 0x01, 0x00, 0x22, 0x02, 0x01, 0x00, 0x21, 0x02, 0x02, 0x00, 0x24, 0x02, 0x3a, 0x00, 0x23, 0x04, 0x00, 0x80, 0x89, 0x44, 0x25, 0x02, 0x80, 0x16, 0x5b]),
        "rf_setup_record_multiple": bytes([0x5a, 0x25, 0x00, 0x06, 0x5d, 0x02, 0xda, 0x01, 0x01, 0x01, 0x20, 0x02, 0x01, 0x00, 0x22, 0x02, 0x01, 0x00, 0x21, 0x02, 0x02, 0x00, 0x24, 0x02, 0x3a, 0x00, 0x23, 0x04, 0x00, 0x80, 0x89, 0x44, 0x25, 0x02, 0x80, 0x16, 0x5b, 0x5a, 0x25, 0x00, 0xa6, 0x26, 0x02, 0xda, 0x01, 0x01, 0x02, 0x20, 0x02, 0x01, 0x00, 0x22, 0x02, 0x01, 0x00, 0x21, 0x02, 0x08, 0x00, 0x24, 0x02, 0x3a, 0x00, 0x23, 0x04, 0x00, 0x80, 0x89, 0x44, 0x25, 0x02, 0xf8, 0x16, 0x5b, 0x5a, 0x25, 0x00, 0xb7, 0x89, 0x02, 0xda, 0x01, 0x01, 0x03, 0x20, 0x02, 0x00, 0x00, 0x22, 0x02, 0x03, 0x00, 0x21, 0x02, 0x02, 0x00, 0x24, 0x02, 0x3c, 0x00, 0x23, 0x04, 0x00, 0x00, 0x7b, 0x44, 0x25, 0x02, 0x35, 0x16, 0x5b, 0x5a, 0x25, 0x00, 0xcf, 0x66, 0x02, 0xda, 0x01, 0x01, 0x04, 0x20, 0x02, 0x00, 0x00, 0x22, 0x02, 0x01, 0x00, 0x21, 0x02, 0x08, 0x00, 0x24, 0x02, 0x3c, 0x00, 0x23, 0x04, 0x00, 0x00, 0x7b, 0x44, 0x25, 0x02, 0xae, 0x16, 0x5b]),
        "settings_record": bytes([0x5a, 0x0e, 0x00, 0xa4, 0x05, 0x07, 0xda, 0x26, 0x04, 0x70, 0x17, 0x00, 0x00, 0x5b]),
        "passing_record": bytes([0x5a, 0x29, 0x00, 0x73, 0x5f, 0x09, 0xda, 0x20, 0x04, 0x44, 0x00, 0x3c, 0x00, 0x01, 0x01, 0x02, 0x21, 0x04, 0x01, 0x00, 0x00, 0x00, 0x02, 0x08, 0xe8, 0xbd, 0xc3, 0x04, 0x00, 0x00, 0x00, 0x00, 0x22, 0x02, 0xfa, 0x08, 0x23, 0x02, 0x00, 0x00, 0x5b]),
        "status_record": bytes([0x5a, 0x61, 0x00, 0x43, 0xc5, 0x0a, 0xda, 0x21, 0x02, 0x2d, 0x10, 0x23, 0x01, 0x01, 0x24, 0x04, 0x00, 0x00, 0x00, 0x00, 0x01, 0x01, 0x01, 0x22, 0x04, 0x00, 0x40, 0x4f, 0x44, 0x01, 0x01, 0x02, 0x22, 0x04, 0x00, 0x80, 0x4f, 0x44, 0x01, 0x01, 0x03, 0x22, 0x04, 0x00, 0x00, 0x00, 0x00, 0x01, 0x01, 0x04, 0x22, 0x04, 0x00, 0x00, 0x00, 0x00, 0x01, 0x01, 0x05, 0x22, 0x04, 0x00, 0x00, 0x00, 0x00, 0x01, 0x01, 0x06, 0x22, 0x04, 0x00, 0x00, 0x00, 0x00, 0x01, 0x01, 0x07, 0x22, 0x04, 0x00, 0x00, 0x00, 0x00, 0x01, 0x01, 0x08, 0x22, 0x04, 0x00, 0x00, 0x00, 0x00, 0x03, 0x02, 0x00, 0x00, 0x5b]),
        "time_record": bytes([0x5a, 0x1c, 0x00, 0xd5, 0x2b, 0x0c, 0xda, 0x02, 0x08, 0x60, 0x51, 0xfc, 0xaf, 0x01, 0x00, 0x00, 0x00, 0x20, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x5b]),
    },
    "tx": {
        "get_rtc_time": bytes([0x5a, 0x0a, 0x00, 0x96, 0xe3, 0x0c, 0xda, 0x02, 0x00, 0x5b]),
        "get_min_lap_time": bytes([0x5a, 0x0e, 0x00, 0xe0, 0x7a, 0x07, 0xda, 0x26, 0x04, 0x00, 0x00, 0x00, 0x00, 0x5b]),
        "get_rf_setup_all": bytes([0x5a, 0x20, 0x00, 0xe0, 0x1e, 0x02, 0xda, 0x01, 0x01, 0x01, 0x01, 0x01, 0x02, 0x01, 0x01, 0x03, 0x01, 0x01, 0x04, 0x01, 0x01, 0x05, 0x01, 0x01, 0x06, 0x01, 0x01, 0x07, 0x01, 0x01, 0x08, 0x5b]),
        "get_rf_setup_single": bytes([0x5a, 0x0b, 0x00, 0x19, 0x5c, 0x9a, 0x02, 0xda, 0x01, 0x01, 0x01, 0x5b]),
        "set_rf_setup_single": bytes([0x5a, 0x25, 0x00, 0x17, 0xdd, 0x02, 0xda, 0x01, 0x01, 0x01, 0x20, 0x02, 0x01, 0x00, 0x21, 0x02, 0x02, 0x00, 0x22, 0x02, 0x03, 0x00, 0x23, 0x04, 0x00, 0x00, 0x61, 0x44, 0x24, 0x02, 0x33, 0x00, 0x25, 0x02, 0x35, 0x16, 0x5b]),
    },
}


class HelperTest(unittest.TestCase):

    def test_gen_crc_table(self):
        """Test generating the CRC table.
        """
        expected = mock_data["crc"]["table"]
        crc_16_table = protocol._gen_crc_16_table()
        self.assertEqual(expected, crc_16_table)

    def test_crc_compute(self):
        """Test computing CRC value.
        """
        expected = 56599
        self.assertEqual(expected, protocol._compute(mock_data["crc"]["record_with_no_crc"]))

    def test_unescape_record(self):
        """Removes escapes from a LapRF record.
        """
        expected = bytes([SOR, ESC, EOR])
        unescaped = protocol._unescape_record(bytes([SOR, ESC, ESC + ESC_OFFSET, EOR]))
        self.assertEqual(unescaped, expected)

    def test_escape_record(self):
        """Places escapes in a LapRF record
        """
        expected = bytes([SOR, ESC, ESC + ESC_OFFSET, ESC,
                          SOR + ESC_OFFSET, ESC, EOR + ESC_OFFSET, EOR])
        escaped = protocol._escape_record(bytes([SOR, ESC, SOR, EOR, EOR]))
        self.assertEqual(escaped, expected)

    def test_split_records(self):
        """Separates multiple records from a packet
        """
        expected = 4
        packet = mock_data["rx"]["rf_setup_record_multiple"]
        records = protocol._split_records(packet)
        self.assertEqual(len(records), expected)


class LapRFProtocolTest(unittest.TestCase):

    def test_decode_rf_setup_record(self):
        """Decode a rfsetup record
        """
        event = protocol._decode_record(bytearray(mock_data['rx']['rf_setup_record_single']))
        self.assertIsInstance(event, protocol.RFSetupEvent)
        self.assertEqual(event.enabled, True)
        self.assertEqual(event.band, 1)
        self.assertEqual(event.channel, 2)
        self.assertEqual(event.gain, 58)
        self.assertEqual(event.threshold, 1100.0)
        self.assertEqual(event.frequency, 5760)
        self.assertTrue(event.is_valid())

    def test_decode_settings_record(self):
        """Decode a settings record
        """
        event = protocol._decode_record(bytearray(mock_data["rx"]["settings_record"]))
        self.assertIsInstance(event, protocol.SettingsEvent)
        self.assertEqual(event.min_lap_time, 6000)
        self.assertTrue(event.is_valid())

    def test_decode_passing_record(self):
        """Decode a passing record
        """
        event = protocol._decode_record(bytearray(mock_data["rx"]["passing_record"]))
        self.assertIsInstance(event, protocol.PassingEvent)
        self.assertEqual(event.decoder_id, 3932228)
        self.assertEqual(event.slot_index, 2)
        self.assertEqual(event.passing_number, 1)
        self.assertEqual(event.rtc_time, 79937000)
        self.assertEqual(event.peak_height, 2298)
        self.assertEqual(event.flags, 0)
        self.assertTrue(event.is_valid())

    def test_decode_status_record(self):
        """Decode a status record
        """
        event = protocol._decode_record(bytearray(mock_data["rx"]["status_record"]))
        self.assertIsInstance(event, protocol.StatusEvent)
        self.assertEqual(event.battery_voltage, 4141)
        self.assertEqual(event.gate_state, 1)
        self.assertEqual(event.detection_count, 0)
        self.assertEqual(event.flags, 0)
        for last_rssi, expected in zip(event.last_rssi, [829, 830, 0, 0, 0, 0, 0, 0]):
            self.assertEqual(last_rssi, expected)
        self.assertTrue(event.is_valid())

    def test_decode_time_record(self):
        """Decode a time record
        """
        event = protocol._decode_record(bytearray(mock_data["rx"]["time_record"]))
        self.assertIsInstance(event, protocol.TimeEvent)
        self.assertEqual(event.rtc_time, 7247516000)
        self.assertTrue(event.is_valid())

    def test_encode_get_rtc_time_record(self):
        """Encode LapRF record to request the RTC time.
        """
        encoded = protocol.encode_get_rtc_time_record()
        self.assertEqual(encoded, mock_data["tx"]["get_rtc_time"])

    def test_encode_get_min_lap_time_record(self):
        """Encode LapRF record to request the minimum lap time setting.
        """
        encoded = protocol.encode_get_min_lap_time_record()
        self.assertEqual(encoded, mock_data["tx"]["get_min_lap_time"])

    # TODO Add test_encode_set_min_lap_time_record

    def test_encode_get_rf_setup_record_single(self):
        """Encode LapRF record to request the configuration of a single receiver slot.
        """
        encoded = protocol.encode_get_rf_setup_record(1)
        self.assertEqual(encoded, mock_data["tx"]["get_rf_setup_single"])

    def test_encode_get_rf_setup_record_all(self):
        """Encode LapRF record to request the configuration for all receiver slots.
        """
        encoded = protocol.encode_get_rf_setup_record()
        self.assertEqual(encoded, mock_data["tx"]["get_rf_setup_all"])

    def test_encode_set_rf_setup_record(self):
        """Encode LapRF record to configure a receiver slot.
        """
        encoded = protocol.encode_set_rf_setup_record(1, True, 3, 2, 5685, 51, 900.0)
        self.assertEqual(encoded, mock_data["tx"]["set_rf_setup_single"])


if __name__ == '__main__':
    unittest.main()
