"""CSV export helpers for daily activity ratings."""

import csv
from pathlib import Path


CSV_COLUMNS = (
    "Date (YYYY-MM-DD)",
    "Activity",
    "Rating",
    "Max sustained wind (mph)",
    "Max gust (mph)",
    "Min temperature (F)",
    "Max rain probability (%)",
    "Limiting variable",
    "Working hours used",
)


def _with_unit(value, unit):
    if value is None:
        return ""
    if isinstance(value, float):
        value = f"{value:g}"
    return f"{value} {unit}"


def build_csv_rows(daily_forecast, daily_ratings, start_label, end_label):
    if len(daily_forecast) != 7 or len(daily_ratings) != 7:
        raise ValueError("CSV export requires exactly 7 forecast days.")

    hours = f"{start_label} to {end_label}"
    rows = []
    activity_fields = (
        ("Crane", "crane"),
        ("Concrete", "concrete"),
        ("Roofing", "roofing"),
    )
    for day, ratings in zip(daily_forecast, daily_ratings):
        for activity, key in activity_fields:
            result = ratings[key]
            row = {
                "Date (YYYY-MM-DD)": day["date"],
                "Activity": activity,
                "Rating": result["rating"],
                "Max sustained wind (mph)": "",
                "Max gust (mph)": "",
                "Min temperature (F)": "",
                "Max rain probability (%)": "",
                "Limiting variable": result["limiting"],
                "Working hours used": hours,
            }
            if activity == "Crane":
                row["Max sustained wind (mph)"] = _with_unit(
                    result["wind"], "mph"
                )
                row["Max gust (mph)"] = _with_unit(result["gust"], "mph")
            elif activity == "Concrete":
                row["Min temperature (F)"] = _with_unit(
                    result["temperature"], "F"
                )
            else:
                row["Max rain probability (%)"] = _with_unit(
                    result["rain"], "%"
                )
            rows.append(row)
    return rows


def write_forecast_csv(path, daily_forecast, daily_ratings,
                       start_label, end_label):
    rows = build_csv_rows(
        daily_forecast, daily_ratings, start_label, end_label
    )
    with Path(path).open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)
