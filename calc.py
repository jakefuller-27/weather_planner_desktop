"""Static layout values for Stage 1."""

from datetime import datetime, timedelta
from urllib.parse import urlencode

DEFAULT_LOCATION = {
    "name": "West Jordan, UT",
    "latitude": 40.6097,
    "longitude": -111.9391,
    "time_zone": "America/Denver",
}

DAYS = (
    "Today · Nov 25",
    "Thu · Nov 26",
    "Fri · Nov 27",
    "Sat · Nov 28",
    "Sun · Nov 29",
    "Mon · Nov 30",
    "Tue · Dec 1",
)

STATUS_COLORS = {
    "GO": "#2E7D32",
    "CAUTION": "#F9A825",
    "NO-GO": "#C62828",
    "NO DATA": "#757575",
}

STATUS_ICONS = {
    "GO": "\u2713",
    "CAUTION": "!",
    "NO-GO": "\u00d7",
    "NO DATA": "?",
}


FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def build_forecast_url(latitude, longitude):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "hourly": (
            "temperature_2m,wind_speed_10m,"
            "wind_gusts_10m,precipitation_probability"
        ),
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "timezone": "auto",
        "forecast_days": 7,
    }
    return f"{FORECAST_URL}?{urlencode(params)}"


def local_day_labels(hourly_times):
    if not hourly_times:
        return list(DAYS)

    first_dates = []
    for timestamp in hourly_times:
        date_text = timestamp[:10]
        if date_text not in first_dates:
            first_dates.append(date_text)

    today = datetime.now().date()
    try:
        today = datetime.strptime(first_dates[0], "%Y-%m-%d").date()
    except (IndexError, ValueError):
        pass

    labels = []
    for offset in range(7):
        date = today + timedelta(days=offset)
        if offset == 0:
            prefix = "Today"
        else:
            prefix = date.strftime("%a")
        labels.append(f"{prefix} · {date.strftime('%b')} {date.day}")
    return labels
