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
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"


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


def build_geocoding_url(name):
    params = {
        "name": name,
        "count": 5,
        "language": "en",
        "format": "json",
    }
    return f"{GEOCODING_URL}?{urlencode(params)}"


def parse_geocoding_results(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get("results"), list):
        return []
    matches = []
    for result in payload["results"][:5]:
        if not isinstance(result, dict):
            continue
        matches.append({
            "name": result.get("name", ""),
            "admin1": result.get("admin1", ""),
            "country": result.get("country", ""),
            "latitude": result.get("latitude"),
            "longitude": result.get("longitude"),
        })
    return matches


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


def aggregate_daily(hourly, start_hour=None, end_hour=None):
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
        if start_hour is not None and end_hour is not None:
            indexes = [
                index for index in indexes
                if start_hour <= int(timestamps[index][11:13]) <= end_hour
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
            if not values:
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


RATING_COLORS = {
    "GO": "#2E7D32",
    "CAUTION": "#F9A825",
    "NO-GO": "#C62828",
    "NO DATA": "#757575",
}


RATING_ICONS = {
    "GO": "\u2713",
    "CAUTION": "!",
    "NO-GO": "\u00d7",
    "NO DATA": "?",
}


def _wind_rating(value):
    if value is None:
        return None
    if value < 15:
        return "GO"
    if value < 20:
        return "CAUTION"
    return "NO-GO"


def _gust_rating(value):
    if value is None:
        return None
    if value < 20:
        return "GO"
    if value < 25:
        return "CAUTION"
    return "NO-GO"


def _worse_rating(ratings):
    rank = {"GO": 0, "CAUTION": 1, "NO-GO": 2}
    available = [rating for rating in ratings if rating is not None]
    if not available:
        return "NO DATA"
    return max(available, key=lambda rating: rank[rating])


def rate_crane(max_wind, max_gust):
    wind = max_wind["value"] if max_wind is not None else None
    gust = max_gust["value"] if max_gust is not None else None
    wind_rating = _wind_rating(wind)
    gust_rating = _gust_rating(gust)

    if wind_rating == "NO-GO" or gust_rating == "NO-GO":
        rating = "NO-GO"
        if wind_rating == "NO-GO" and gust_rating == "NO-GO":
            limiting = "sustained wind" if wind >= gust else "gust"
        elif wind_rating == "NO-GO":
            limiting = "sustained wind"
        else:
            limiting = "gust"
    elif wind_rating is None or gust_rating is None:
        rating = "NO DATA"
        limiting = "sustained wind" if wind_rating is None else "gust"
    else:
        rating = _worse_rating((wind_rating, gust_rating))
        if wind_rating == gust_rating:
            limiting = "sustained wind and gust"
        elif wind_rating == rating:
            limiting = "sustained wind"
        else:
            limiting = "gust"

    return {
        "rating": rating,
        "limiting": limiting,
        "wind": wind,
        "wind_rating": wind_rating,
        "wind_time": max_wind["time"] if max_wind is not None else None,
        "gust": gust,
        "gust_rating": gust_rating,
        "gust_time": max_gust["time"] if max_gust is not None else None,
    }


def rate_concrete(min_temperature):
    temperature = (
        min_temperature["value"] if min_temperature is not None else None
    )
    if temperature is None:
        return {"rating": "NO DATA", "limiting": "minimum temperature",
                "temperature": None, "time": None}
    if temperature >= 40:
        rating = "GO"
    elif temperature >= 32:
        rating = "CAUTION"
    else:
        rating = "NO-GO"
    return {"rating": rating, "limiting": "minimum temperature",
            "temperature": temperature, "time": min_temperature["time"]}


def rate_roofing(max_rain):
    rain = max_rain["value"] if max_rain is not None else None
    if rain is None:
        return {"rating": "NO DATA", "limiting": "maximum rain probability",
                "rain": None, "time": None}
    if rain < 20:
        rating = "GO"
    elif rain < 50:
        rating = "CAUTION"
    else:
        rating = "NO-GO"
    return {"rating": rating, "limiting": "maximum rain probability",
            "rain": rain, "time": max_rain["time"]}


def rate_daily(day):
    return {
        "crane": rate_crane(day["max_wind"], day["max_gust"]),
        "concrete": rate_concrete(day["min_temperature"]),
        "roofing": rate_roofing(day["max_rain"]),
    }
