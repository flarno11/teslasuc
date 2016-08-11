import unittest
import datetime
from lib import TimePattern, TimeFormat
from run_import import chargers, pattern_suc


class DateTest(unittest.TestCase):
    def setUp(self):
        pass

    def test_parse(self):
        s = "2016-07-28T11:05:00.000Z"
        self.assertIsNotNone(TimePattern.match(s))

        d = datetime.datetime.strptime(s, TimeFormat)
        self.assertEquals(11, d.hour)
        self.assertEquals(5, d.minute)


class ParseTest(unittest.TestCase):
    def setUp(self):
        pass

    def test_suc_0(self):
        s = "<p><strong>Charging</strong><br />0 Superchargers, available 24/7</p>"
        self.assertEquals(0, chargers(s))

    def test_suc_1(self):
        s = "<p><strong>Charging</strong><br />1 Superchargers, available 24/7</p>"
        self.assertEquals(1, chargers(s))

    def test_suc_10(self):
        s = "<p><strong>Charging</strong><br />10 Superchargers, available 24/7</p>"
        self.assertEquals(10, chargers(s))

    def test_dec_0(self):
        s = "<p><strong>Charging</strong><br />0 Tesla Connector, up to 22kW.<br />Available for patrons only. Self park.</p>"
        self.assertEquals(0, chargers(s))

    def test_dec_10(self):
        s = "<p><strong>Charging</strong><br />10 Tesla Connector, up to 22kW.<br />Available for patrons only. Self park.</p>"
        self.assertEquals(10, chargers(s))
