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


def format_local_hour(timestamp):
    """Return a local 12-hour timestamp label with am/pm."""
    try:
        hour_text = str(timestamp)[11:16]
        hour = int(hour_text[:2])
        minute = int(hour_text[3:5])
    except (TypeError, ValueError):
        return str(timestamp)

    suffix = "am" if hour < 12 else "pm"
    display_hour = hour % 12 or 12
    return f"{display_hour}:{minute:02d} {suffix}"


def _valid_pairs(values, timestamps):
    """Preserve source order and exclude missing values."""
    pairs = []
    for index, (timestamp, value) in enumerate(zip(timestamps, values)):
        if value is not None:
            pairs.append((timestamp, value, index))
    return pairs


def _aggregate_variable(values, timestamps, maximum):
    pairs = _valid_pairs(values, timestamps)
    if not pairs:
        return None

    target = (max if maximum else min)(pair[1] for pair in pairs)
    first = next(pair for pair in pairs if pair[1] == target)
    return {
        "value": target,
        "hour": first[0],
        "time": format_local_hour(first[0]),
        "available": True,
    }


def aggregate_daily(hourly):
    """
    Aggregate 24 hourly values for each local calendar date.

    Missing values make only the corresponding variable unavailable. Ties use
    the first hourly occurrence, and source order is preserved.
    """
    if not isinstance(hourly, dict):
        return []

    timestamps = hourly.get("time")
    if not isinstance(timestamps, list):
        return []

    variable_names = (
        "wind_speed_10m",
        "wind_gusts_10m",
        "temperature_2m",
        "precipitation_probability",
    )
    if any(name not in hourly or not isinstance(hourly[name], list)
           for name in variable_names):
        return []

    dates = []
    for timestamp in timestamps:
        if not isinstance(timestamp, str):
            continue
        date = timestamp[:10]
        if date not in dates:
            dates.append(date)

    daily = []
    for date in dates:
        indexes = [
            index for index, timestamp in enumerate(timestamps)
            if isinstance(timestamp, str) and timestamp.startswith(date)
        ]
        if not indexes:
            continue

        day_times = [timestamps[index] for index in indexes]
        day_wind = [hourly["wind_speed_10m"][index]
                    if index < len(hourly["wind_speed_10m"]) else None
                    for index in indexes]
        day_gust = [hourly["wind_gusts_10m"][index]
                    if index < len(hourly["wind_gusts_10m"]) else None
                    for index in indexes]
        day_temperature = [hourly["temperature_2m"][index]
                           if index < len(hourly["temperature_2m"]) else None
                           for index in indexes]
        day_rain = [hourly["precipitation_probability"][index]
                    if index < len(hourly["precipitation_probability"]) else None
                    for index in indexes]

        def aggregate(values, maximum):
            if len(values) != 24:
                return None
            if any(value is None for value in values):
                return None
            return _aggregate_variable(values, day_times, maximum)

        daily.append({
            "date": date,
            "max_wind": aggregate(day_wind, True),
            "max_gust": aggregate(day_gust, True),
            "min_temperature": aggregate(day_temperature, False),
            "max_rain": aggregate(day_rain, True),
        })

    return daily


# Public names for callers that prefer descriptive terminology.
aggregate_hourly_forecast = aggregate_daily
aggregate_daily_forecast = aggregate_daily
