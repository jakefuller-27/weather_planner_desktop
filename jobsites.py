"""JSON persistence for saved jobsite selections."""

import json
import math
import re
from pathlib import Path


_HOUR_LABEL = re.compile(r"^(1[0-2]|[1-9]):00 (AM|PM)$|^11:59 PM$")


def _hour_number(label):
    if not isinstance(label, str) or not _HOUR_LABEL.fullmatch(label):
        raise ValueError("Working-hour values must use the provided hour options.")
    if label == "11:59 PM":
        return 23 * 60 + 59

    time, meridiem = label.split()
    hour_text, minute_text = time.split(":")
    hour = int(hour_text)
    minute = int(minute_text)
    if meridiem == "AM":
        hour = 0 if hour == 12 else hour
    else:
        hour = 12 if hour == 12 else hour + 12
    return hour * 60 + minute


def validate_jobsite(data):
    if not isinstance(data, dict):
        raise ValueError("The selected file must contain a JSON object.")

    name = data.get("jobsite_name")
    time_zone = data.get("time_zone")
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    start_hour = data.get("start_hour")
    end_hour = data.get("end_hour")

    if not isinstance(name, str) or not name.strip():
        raise ValueError("The saved jobsite name is missing.")
    if not isinstance(time_zone, str) or not time_zone.strip():
        raise ValueError("The saved time zone is missing.")
    if (isinstance(latitude, bool) or not isinstance(latitude, (int, float))
            or not math.isfinite(latitude) or not -90 <= latitude <= 90):
        raise ValueError("The saved latitude must be between -90 and 90.")
    if (isinstance(longitude, bool) or not isinstance(longitude, (int, float))
            or not math.isfinite(longitude) or not -180 <= longitude <= 180):
        raise ValueError("The saved longitude must be between -180 and 180.")

    start_value = _hour_number(start_hour)
    end_value = _hour_number(end_hour)
    if end_value <= start_value:
        raise ValueError("Saved End working hour must be later than Start.")

    return {
        "jobsite_name": name.strip(),
        "latitude": float(latitude),
        "longitude": float(longitude),
        "time_zone": time_zone.strip(),
        "start_hour": start_hour,
        "end_hour": end_hour,
        "start_hour_value": start_value,
        "end_hour_value": end_value,
    }


def save_jobsite(path, data):
    validated = validate_jobsite(data)
    payload = {
        "jobsite_name": validated["jobsite_name"],
        "latitude": validated["latitude"],
        "longitude": validated["longitude"],
        "time_zone": validated["time_zone"],
        "start_hour": validated["start_hour"],
        "end_hour": validated["end_hour"],
    }
    with Path(path).open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)
        file.write("\n")


def load_jobsite(path):
    with Path(path).open("r", encoding="utf-8") as file:
        data = json.load(file)
    return validate_jobsite(data)
