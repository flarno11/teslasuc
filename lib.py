import re
import datetime


TimePattern = re.compile("^[0-9]{4}\-[0-9]{2}\-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}Z$")
TimeFormat = "%Y-%m-%dT%H:%M:%S.%fZ"


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