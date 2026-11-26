"""Validation for Stage 3 Case 1 (Fixture A)."""

from calc import aggregate_daily


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


if __name__ == "__main__":
    main()
