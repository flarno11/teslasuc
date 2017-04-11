import re
import datetime
from collections import OrderedDict

TimePattern = re.compile("^[0-9]{4}\-[0-9]{2}\-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z$")
TimeFormat = "%Y-%m-%dT%H:%M:%S.%fZ"

TimePatternSimple = re.compile("^[0-9]{4}\-[0-9]{2}\-[0-9]{2} [0-9]{2}:[0-9]{2}$")
TimeFormatSimple = "%Y-%m-%d %H:%M"


def convert_time_fields(item):
    if not item:
        return
    for k, v in item.iteritems():
        if v is None:
            continue

        if isinstance(v, dict):
            convert_time_fields(v)
        elif TimePattern.match(v):
            item[k] = datetime.datetime.strptime(v, TimeFormat)


def convert_to_csv(items):
    def escape(s):
        if type(s) is str and ',' in s:
            return '"' + s + '"'
        return str(s)

    def join(items):
        return ','.join(map(lambda i: escape(i), items))

    header = join(items[0].keys())
    lines = [join(item.values()) for item in items]
    return header + "\n" + "\n".join(lines)


def parse_user_accept_languages(header):
    if header:
        return list(OrderedDict.fromkeys(map(lambda h: h.split(';')[0].split('-')[0], header.split(','))))
    else:
        return []
