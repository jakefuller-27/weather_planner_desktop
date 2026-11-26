"""Validation for Stage 3 Case 1 (Fixture A)."""

import json
import ssl
import urllib.request

from calc import (
    aggregate_daily,
    build_geocoding_url,
    parse_geocoding_results,
    rate_crane,
    rate_concrete,
    rate_roofing,
)


FIXTURE_A = {
    "time": [
        f"2026-04-14T{hour:02d}:00" for hour in range(24)
    ],
    "wind_speed_10m": [
        10, 12, 14, 14, 13, 11, 10, 9,
        8, 9, 12, 15, 16, 18, 18, 17,
        16, 15, 14, 13, 12, 11, 10, 10,
    ],
    "wind_gusts_10m": [
        15, 16, 18, 20, 20, 19, 18, 17,
        16, 18, 20, 22, 24, 26, 26, 24,
        23, 22, 21, 20, 19, 18, 17, 16,
    ],
    "temperature_2m": [
        41, 40, 39, 38, 37, 36, 35, 34,
        33, 32, 31, 30, 29, 28, 27, 28,
        29, 30, 31, 32, 33, 34, 36, 38,
    ],
    "precipitation_probability": [
        5, 5, 10, 10, 12, 15, 15, 20,
        20, 25, 30, 35, 40, 45, 50, 55,
        60, 55, 50, 45, 40, 30, 20, 10,
    ],
}


EXPECTED_A = {
    "date": "2026-04-14",
    "max_wind": 18,
    "max_wind_hour": "1:00 pm",
    "max_gust": 26,
    "max_gust_hour": "1:00 pm",
    "min_temperature": 27,
    "min_temperature_hour": "2:00 pm",
    "max_rain": 60,
    "max_rain_hour": "4:00 pm",
}


def main():
    daily = aggregate_daily(FIXTURE_A)
    assert len(daily) == 1, f"expected 1 day, got {len(daily)}"
    day = daily[0]

    actual = {
        "date": day["date"],
        "max_wind": day["max_wind"]["value"],
        "max_wind_hour": day["max_wind"]["time"],
        "max_gust": day["max_gust"]["value"],
        "max_gust_hour": day["max_gust"]["time"],
        "min_temperature": day["min_temperature"]["value"],
        "min_temperature_hour": day["min_temperature"]["time"],
        "max_rain": day["max_rain"]["value"],
        "max_rain_hour": day["max_rain"]["time"],
    }
    assert actual == EXPECTED_A, (
        f"Fixture A mismatch\nexpected: {EXPECTED_A}\nactual:   {actual}"
    )

    tied = dict(FIXTURE_A)
    tied["wind_speed_10m"] = [18] * 24
    tied_day = aggregate_daily(tied)[0]
    assert tied_day["max_wind"]["time"] == "12:00 am"

    missing = dict(FIXTURE_A)
    missing["temperature_2m"] = list(FIXTURE_A["temperature_2m"])
    missing["temperature_2m"][7] = None
    missing_day = aggregate_daily(missing)[0]
    assert missing_day["min_temperature"] is None

    print("Case 1 (Fixture A): PASS")
    print(actual)

    case_2()
    case_3()
    case_4()
    case_6()


def _value(value, time="12:00 am"):
    return {"value": value, "time": time, "available": True}


def case_2():
    wind_cases = [
        (14.9, "GO"),
        (15, "CAUTION"),
        (19.9, "CAUTION"),
        (20, "NO-GO"),
    ]
    for value, expected in wind_cases:
        result = rate_crane(_value(value), _value(10))
        assert result["rating"] == expected, (
            f"wind boundary {value}: {result['rating']} != {expected}"
        )

    gust_cases = [
        (19.9, "GO"),
        (20, "CAUTION"),
        (24.9, "CAUTION"),
        (25, "NO-GO"),
    ]
    for value, expected in gust_cases:
        result = rate_crane(_value(10), _value(value))
        assert result["rating"] == expected, (
            f"gust boundary {value}: {result['rating']} != {expected}"
        )

    concrete_cases = [(40, "GO"), (39.9, "CAUTION"),
                      (32, "CAUTION"), (31.9, "NO-GO")]
    for value, expected in concrete_cases:
        result = rate_concrete(_value(value))
        assert result["rating"] == expected

    roofing_cases = [(19.9, "GO"), (20, "CAUTION"),
                     (49.9, "CAUTION"), (50, "NO-GO")]
    for value, expected in roofing_cases:
        result = rate_roofing(_value(value))
        assert result["rating"] == expected

    crane_wind_missing = rate_crane(None, _value(30))
    assert crane_wind_missing["rating"] == "NO-GO"
    crane_gust_missing = rate_crane(_value(30), None)
    assert crane_gust_missing["rating"] == "NO-GO"
    both_missing = rate_crane(None, None)
    assert both_missing["rating"] == "NO DATA"

    print("Case 2 (threshold boundaries): PASS")


def case_3():
    wind_values = [0, 14.999, 15, 19.999, 20, 35]
    gust_values = [0, 19.999, 20, 24.999, 25, 40]
    temperature_values = [31, 31.999, 32, 39.999, 40, 50]
    rain_values = [0, 19.999, 20, 49.999, 50, 100]
    rank = {"GO": 0, "CAUTION": 1, "NO-GO": 2}

    for wind in wind_values:
        for gust in gust_values:
            result = rate_crane(_value(wind), _value(gust))
            wind_rating = (
                "GO" if wind < 15 else
                "CAUTION" if wind < 20 else "NO-GO"
            )
            gust_rating = (
                "GO" if gust < 20 else
                "CAUTION" if gust < 25 else "NO-GO"
            )
            expected = max(
                (wind_rating, gust_rating),
                key=lambda rating: rank[rating],
            )
            assert result["rating"] == expected

    for temperature in temperature_values:
        expected = "GO" if temperature >= 40 else (
            "CAUTION" if temperature >= 32 else "NO-GO"
        )
        assert rate_concrete(_value(temperature))["rating"] == expected

    for rain in rain_values:
        expected = "GO" if rain < 20 else (
            "CAUTION" if rain < 50 else "NO-GO"
        )
        assert rate_roofing(_value(rain))["rating"] == expected

    print("Case 3 (property check): PASS")


def case_4():
    day = aggregate_daily(FIXTURE_A, start_hour=7, end_hour=16)[0]
    actual = {
        "max_wind": day["max_wind"]["value"],
        "max_wind_hour": day["max_wind"]["time"],
        "max_gust": day["max_gust"]["value"],
        "max_gust_hour": day["max_gust"]["time"],
        "min_temperature": day["min_temperature"]["value"],
        "min_temperature_hour": day["min_temperature"]["time"],
        "max_rain": day["max_rain"]["value"],
        "max_rain_hour": day["max_rain"]["time"],
    }
    expected = {
        "max_wind": 18,
        "max_wind_hour": "1:00 pm",
        "max_gust": 26,
        "max_gust_hour": "1:00 pm",
        "min_temperature": 27,
        "min_temperature_hour": "2:00 pm",
        "max_rain": 60,
        "max_rain_hour": "4:00 pm",
    }
    assert actual == expected, (
        f"Case 4 mismatch\nexpected: {expected}\nactual:   {actual}"
    )
    print("Case 4 (working hours 7:00 AM to 4:00 PM): PASS")
    print(actual)


def case_6():
    context = ssl.create_default_context(cafile="/etc/ssl/cert.pem")
    request = urllib.request.Request(
        build_geocoding_url("Provo"),
        headers={"Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=20, context=context) as response:
        payload = json.loads(response.read().decode("utf-8"))
    matches = parse_geocoding_results(payload)
    provo = next(
        (
            match for match in matches
            if match["name"].lower() == "provo"
            and match["admin1"] == "Utah"
        ),
        None,
    )
    assert provo is not None, "Provo, Utah was not in geocoding results"
    assert abs(provo["latitude"] - 40.23) <= 0.1
    assert abs(provo["longitude"] - (-111.66)) <= 0.1
    print("Case 6 (city search for Provo): PASS")
    print(provo)


if __name__ == "__main__":
    main()
