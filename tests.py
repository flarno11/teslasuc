import unittest
import datetime
from lib import TimePattern, TimeFormat


class DateTest(unittest.TestCase):
    def setUp(self):
        pass

    def test_parse(self):
        s = "2016-07-28T11:05:00.000Z"
        self.assertIsNotNone(TimePattern.match(s))

        d = datetime.datetime.strptime(s, TimeFormat)
        self.assertEquals(11, d.hour)
        self.assertEquals(5, d.minute)
