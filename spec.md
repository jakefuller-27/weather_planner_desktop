# Specification

# Jobsite Weather Planner

## Overview
This is a single-file weather planning app that opens with West Jordan selected and a live 7-day Open-Meteo forecast. Leaflet and OpenStreetMap let the user move the jobsite marker anywhere on Earth. The app separately rates crane, concrete, and roofing work for each local calendar day and provides a reasons panel explaining the values and thresholds behind each result. It includes desktop and phone layouts, loading and error states, refresh controls, a legend, a crane-height warning, and a planning disclaimer.

## Purpose
Lets a construction manager click a jobsite on a map and see which of the next 7 local calendar days are GO, CAUTION, NO-GO, or NO DATA for crane lifts, concrete pours, and roofing.

## Inputs
- Jobsite location:
  - Control: click a Leaflet map to move the jobsite marker.
  - Leaflet: use Leaflet `1.9.4` from unpkg.
  - Map tiles: OpenStreetMap tiles with the required attribution.
  - Range: any location on Earth.
  - Units: latitude and longitude in decimal degrees.
  - Default: West Jordan, UT (`40.6097`, `-111.9391`) is selected.
  - Initial map view: zoom level `9`, centered on West Jordan.
  - Location name: latitude and longitude to 4 decimal places, followed by the time zone name returned by Open-Meteo.
  - No API keys, address search, geocoding, or reverse geocoding are used.

## Data source and assumptions
- Use `https://api.open-meteo.com/v1/forecast` with these parameters:
  - `latitude`
  - `longitude`
  - `hourly=temperature_2m,wind_speed_10m,wind_gusts_10m,precipitation_probability`
  - `temperature_unit=fahrenheit`
  - `wind_speed_unit=mph`
  - `timezone=auto`
  - `forecast_days=7`
- Display forecast values in mph and °F.
- The 7 days are today plus the next 6 local calendar days in the location's time zone, with 24 hourly values for each day.
- All 24 hours count; there is no work-hour filter.
- Fetch automatically when the location is clicked and manually when the Refresh button is used.
- There is no automatic timer and no automatic retry.
- On failure for a new click, keep the previous jobsite, marker, and map view. Show "Could not load the forecast." and a Try again button.
- Try again repeats the forecast request for the current selected jobsite.
- Show "Forecast pulled at [browser local date and time]" under the calendar. This is the pull time, not Open-Meteo's model update time.

## Calculations
- Compute each day from the hourly forecast:
  - Maximum `wind_speed_10m` in mph.
  - Maximum `wind_gusts_10m` in mph.
  - Minimum `temperature_2m` in °F.
  - Maximum `precipitation_probability` in percent.
- If two hours tie for a maximum or minimum value, report and use the first hour.
- If any hourly value needed for a variable is missing for that day, that variable is unavailable and the activity rating is NO DATA (gray).
- NO DATA is not NO-GO.
- If at least one available crane variable already makes the crane NO-GO, the crane remains NO-GO even if another variable is unavailable.
- There is no overall daily rating. Crane, concrete, and roofing are rated separately.
- Crane rating:
  - Sustained wind GO: `< 15 mph`.
  - Sustained wind CAUTION: `>= 15 mph and < 20 mph`.
  - Sustained wind NO-GO: `>= 20 mph`.
  - Gust GO: `< 20 mph`.
  - Gust CAUTION: `>= 20 mph and < 25 mph`.
  - Gust NO-GO: `>= 25 mph`.
  - Use the worse of the sustained-wind rating and gust rating.
- Concrete rating:
  - GO: low temperature `>= 40°F`.
  - CAUTION: low temperature `>= 32°F and < 40°F`.
  - NO-GO: low temperature `< 32°F`.
- Roofing rating:
  - GO: maximum rain probability `< 20%`.
  - CAUTION: maximum rain probability `>= 20% and < 50%`.
  - NO-GO: maximum rain probability `>= 50%`.
- The click explanation names the limiting variable and its calculated value.

### Threshold sources and assumptions
- Every threshold is an app planning rule, not a manufacturer limit or code limit.
- The concrete `32°F` no-go line is the app's own rule.
- Crane operations must follow the crane manufacturer's wind limits and the applicable load chart. See OSHA 29 CFR 1926.1417, "Operation—procedures," [eCFR](https://www.ecfr.gov/current/title-29/subtitle-B/chapter-XVII/part-1926/subpart-CC/subjectgroup-ECFR21aa669433f4751/section-1926.1417).
- The crane thresholds are a conservative planning policy: wind below 15 mph is GO, wind of 15–19.9 mph or gusts of 20–24.9 mph are CAUTION, and wind of 20 mph or more or gusts of 25 mph or more are NO-GO. This policy is not specified by a code or manufacturer and must be replaced or overridden by project or crane-specific limits.
- Every crane result shows: "Wind is forecast at 10 m above ground and likely understates wind at boom height. Always follow the crane manufacturer's limits and site wind readings."
- The concrete thresholds are app planning rules informed by ACI 306 guidance for cold-weather concreting, which identifies conditions near or below 40°F for cold-weather procedures and freezing protection. See [ACI 306R-16, Guide to Cold Weather Concreting](https://www.concrete.org/store/productdetail.aspx?ItemID=306R16) and [ACI 306.1-90, Standard Specification for Cold Weather Concreting](https://www.concrete.org/store/productdetail.aspx?ItemID=306.1).
- The roofing thresholds are app planning rules. Precipitation probability means the chance of precipitation at the location, not the expected surface wetness or rain amount. See the [National Weather Service Probability of Precipitation](https://www.weather.gov/ama/Probability_of_Precipitation). Wet or slippery surfaces must still be managed under OSHA 29 CFR 1926.501; see [OSHA 1926.501](https://www.osha.gov/laws-regs/regulations/standardnumber/1926/1926.501).

## Outputs
- Desktop calendar:
  - 3 rows: crane, concrete, and roofing.
  - 7 columns: today plus the next 6 local calendar days.
  - The calendar uses the full width.
- Phone calendar:
  - Each day is a card listing its three separate ratings.
- Each activity/day cell shows one word and an icon:
  - GO: `#2E7D32`.
  - CAUTION: `#F9A825` with dark text.
  - NO-GO: `#C62828`.
  - NO DATA: `#757575`.
- Accent color: `#1F4E79`.
- Font: system font stack.
- Each cell also shows all values used for that activity:
  - Crane: maximum sustained wind in mph and maximum gust in mph.
  - Concrete: minimum temperature in °F.
  - Roofing: maximum rain probability in percent.
- Clicking a cell opens a reasons panel below the calendar.
- The reasons panel shows:
  - Activity.
  - Date.
  - Rating word.
  - Each variable used for the activity with its daily value and units.
  - The threshold compared to that variable.
  - The limiting variable.
  - The local 12-hour time with am/pm of the first hour the daily value occurred.
  - For crane: sustained wind and gust values and thresholds, plus which variable was limiting.
  - For concrete: minimum temperature only.
  - For roofing: maximum rain probability only.
- The legend is under the calendar and uses words and icons, not color alone:
  - GO: green with a check mark.
  - CAUTION: yellow with an exclamation mark.
  - NO-GO: red with an X.
  - NO DATA: gray with a question mark.
- Footer disclaimer: "Ratings are planning aids only, not work authorization. Follow your site safety plan, manufacturer limits, and applicable codes."

## Look and feel
- Layout order from top:
  - Title and hint.
  - Map.
  - Jobsite information with Refresh button.
  - Calendar.
  - Legend.
  - Reasons panel.
  - Disclaimer.
- Page title: "Jobsite Weather Planner".
- Hint: "Click the map to move the jobsite. Click a calendar cell to see why."
- Use a deep-blue and cool-gray palette, system font stack, strong contrast, clear boundaries, and slightly rounded cards with compact professional density.
- Status text and symbols always appear with status colors.
- Provide visible keyboard focus and sufficient tap targets on phones.
- On first open:
  - Center the map on West Jordan at zoom level `9`.
  - Select the West Jordan marker.
  - Load the forecast.
  - The calendar is never empty.
- Desktop: show the map above the full-width 7-day calendar.
- Phone: show the map above the day-card calendar.
- Loading: show "Loading forecast..." in place of the calendar.
- Failure: show "Could not load the forecast." in red and a Try again button.
- A failed new click keeps the previous jobsite, marker, map view, and forecast unchanged.
- Under the calendar, show "Forecast pulled at [browser local date and time]" using browser local date and time.
- Near the calendar, show latitude and longitude to 4 decimals plus the Open-Meteo time zone name.
- Use consistent status areas and preserve reduced-motion, zoom, and responsive resizing behavior.

## Validation
- Location: West Jordan (40.6097, -111.9391)
- Date: [DATE]
- Pulled at: [TIME]
- Raw daily values from the hourly forecast:
  - Maximum wind: [X] mph at [hour]
  - Maximum gust: [X] mph at [hour]
  - Minimum temperature: [X] °F at [hour]
  - Maximum rain probability: [X]% at [hour]
- Hand-worked ratings:
  - Crane: [RATING] because [reason]
  - Concrete: [RATING] because [reason]
  - Roofing: [RATING] because [reason]
- NWS comparison: [paste what weather.gov showed]

- App result:
- Match? yes/no:

## Validation results

| Case | Expected | Actual | Result |
|---|---|---|---|
| 1 - Fixture A | Wind 18 mph at 1:00 pm; gust 26 mph at 1:00 pm; minimum temperature 27 F at 2:00 pm; rain probability 60% at 4:00 pm | Wind 18 mph at 1:00 pm; gust 26 mph at 1:00 pm; minimum temperature 27 F at 2:00 pm; rain probability 60% at 4:00 pm | PASS |
| 2 - Threshold boundaries | Wind 14.9 GO, 15/19.9 CAUTION, 20 NO-GO; gust 19.9 GO, 20/24.9 CAUTION, 25 NO-GO; concrete 40 GO, 32–<40 Caution, <32 NO-GO; rain <20 GO, 20–<50 CAUTION, >=50 NO-GO; crane NO-GO precedence and NO DATA behavior | All threshold boundary and missing-variable assertions matched | PASS |
| 3 - Property check | Every sampled crane, concrete, and roofing combination follows the specified threshold formulas | All sampled property combinations matched | PASS |
| 4 - Working hours 7:00 AM–4:00 PM | Wind 18 mph at 1:00 pm; gust 26 mph at 1:00 pm; minimum temperature 27 F at 2:00 pm; rain probability 60% at 4:00 pm | Wind 18 mph at 1:00 pm; gust 26 mph at 1:00 pm; minimum temperature 27 F at 2:00 pm; rain probability 60% at 4:00 pm | PASS |
| 6 - City search Provo | Provo, Utah, within 0.1 degrees of latitude 40.23 and longitude -111.66 | Provo, Utah: 40.23384, -111.65853 | PASS |

### In-app check (done by me)
I opened the app, clicked today's crane, concrete, and roofing cells for West Jordan, and confirmed the values and ratings match my hand-worked values.

### Case 5: Live check (reference: Open-Meteo raw data and weather.gov)
- Location: West Jordan (40.6097, -111.9391). Date: Thu Nov 26, 2026. Pulled at: about 8:47 AM.
- Raw daily values worked by hand from the hourly forecast: max wind 6.7 mph at 2:00 AM; max gust 11.2 mph at 11:00 AM; min temperature 26.9 °F at 5:00 AM; max rain probability 0% at 12:00 AM (all hours tie, first hour used).
- Hand-worked ratings: crane GO (wind under 15 and gust under 20); concrete NO-GO (26.9 is under 32); roofing GO (0% is under 20).
- App result: the app calculated the same values and ratings. Match: yes.
- NWS comparison (weather.gov): weather.gov (forecast for 2 Miles W Midvale, UT, with current conditions from South Valley Regional Airport, last updated Nov 26 at 8:35 AM MST) showed 32 °F and south wind at 6 mph at 8:35 AM; Thanksgiving Day mostly sunny with a high near 52 °F, light and variable wind, and no precipitation chance shown; tonight a low around 35 °F. Open-Meteo showed a high of 51.2 °F at 3:00 PM, 35.6 °F at 11:00 PM, a max wind of 6.7 mph, and 0% rain probability. These agree closely. weather.gov does not list today's overnight low, but its 32 °F reading at 8:35 AM, with Open-Meteo showing 28.2 °F at 8:00 AM and 32.5 °F at 9:00 AM, is consistent with a freezing morning, so the concrete NO-GO rating is supported. The two sources use different forecast models, and weather.gov's point is near Midvale while the app uses West Jordan.


## Out of scope
- No forecasts beyond 7 days.
- No saving of jobsites.
- No activities besides crane, concrete, roofing.

## Features

### Feature 1: Crew working hours
- **Inputs**
  - Provide a Start hour dropdown and an End hour dropdown in 12-hour format.
  - Default to 12:00 AM for Start and 11:59 PM for End.
  - End must be later than Start.
  - If End is not later than Start, show a clear validation message and keep the previously valid working-hours window.
- **Calculations**
  - Use only hourly forecast values whose hour falls inside the selected working-hours window.
  - Compute each day's maximum wind, maximum gust, minimum temperature, and maximum rain probability from only those in-window hourly values.
  - If values tie for a maximum or minimum, use the first hour.
- **Outputs**
  - The reasons panel shows the working hours used for the selected activity/day.
  - Show a line under the calendar: "Ratings use working hours [start] to [end]."
- **Validation**
  - Use the same West Jordan location and date as the main validation case.
  - Use working hours 7:00 AM to 4:00 PM.
  - Compute the daily values from only the 10 hourly values in that window.
  - Hand-worked values:
    - Maximum wind: [X] mph at [hour]
    - Maximum gust: [X] mph at [hour]
    - Minimum temperature: [X] °F at [hour]
    - Maximum rain probability: [X]% at [hour]
  - Hand-worked ratings:
    - Crane: [RATING]
    - Concrete: [RATING]
    - Roofing: [RATING]
  - App result: [paste]
  - Match: [yes/no]
- **Out of scope**
  - Overnight shifts.
  - Different working hours for different activities.

### Feature 2: City search
- **Inputs**
  - Provide a text box with a Search button above the map.
  - Use the placeholder "Search for a city".
  - Require at least 2 characters before searching.
  - Start a search when the user presses Enter or clicks Search.
  - The feature uses no API key.
- **Data source**
  - Use `https://geocoding-api.open-meteo.com/v1/search`.
  - Send `name`, `count=5`, `language=en`, and `format=json`.
- **Calculations**
  - No new calculations are introduced.
  - Selecting a result runs the existing forecast logic used for a map click, using the result's latitude and longitude.
- **Outputs**
  - Display up to 5 matches in the format "Name, Region, Country".
  - Picking a match moves the marker, centers the map at zoom 10, and loads the forecast.
  - Show the chosen match name in the jobsite label.
  - Show "No matches found." when the search returns no results.
  - Show "Search failed. Try again." when the geocoding request fails.
- **Validation**
  - Search "Provo".
  - Pick Provo, Utah.
  - Confirm the result coordinates are within 0.1 degrees of 40.23 latitude and -111.66 longitude.
  - Confirm the forecast loads for that location.
  - Result: [paste]
  - Match: [yes/no]
- **Out of scope**
  - Autocomplete while typing.
  - Saved searches.
  - Street addresses.

## Resolved notes
- Replaced Google Maps and address/geocoding search with Leaflet `1.9.4`, OpenStreetMap tiles, and map-click-only location selection.
- Made West Jordan, UT the loaded initial jobsite and allowed locations anywhere on Earth.
- Removed the overall daily rating; crane, concrete, and roofing are separate.
- Defined NO DATA, tie-hour, missing-hour, refresh, retry, pull-time, and first-hour behavior.
- Added exact colors, system font, desktop/phone layouts, reasons-panel fields, legend, and disclaimer.
- Replaced calendar-empty and failed-location behavior with a guaranteed initial forecast and preservation of the prior valid state.

## Build stages

### Stage 1: Static page and layout mockup
- Build the title and hint, Leaflet map container centered on West Jordan at zoom 9, jobsite information area with Refresh, desktop 3-by-7 grid and phone day cards, legend, empty reasons panel, loading/error placeholders, and disclaimer.
- Check desktop and phone layouts, overflow, layout order, map attribution, status colors and icons, keyboard focus, tap targets, and that no live calculations are present.

### Stage 2: Open-Meteo request and location behavior
- Add the exact Open-Meteo endpoint and hourly parameters, initial West Jordan request, map-click location changes, loading/error states, Try again, Refresh, and preservation of the previous valid state after a failure.
- Check startup loading, multiple map selections including outside the U.S., 7 local calendar days, 24 hourly values, mph and °F values, pull time, location name, time zone, retry, refresh, and failure behavior.

### Stage 3: Daily forecast aggregation
- Calculate each day's maximum sustained wind and gust, minimum temperature, maximum rain probability, first-occurrence hour for each value, tied-hour behavior, and missing-variable handling.
- Check a known hourly fixture for maximum, minimum, tied hours, day grouping, units, and missing values.

### Stage 4: Ratings and reasons panel
- Apply crane, concrete, and roofing thresholds; use the worse crane rating; implement NO DATA and crane NO-GO precedence; open the reasons panel for selected cells; include thresholds, limiting variable, units, first hours, and the crane 10 m-height note.
- Check every threshold boundary, tie and limiting-variable rules, 12-hour am/pm times, and the absence of an overall daily rating.

### Stage 5: Responsive polish and validation
- Finish exact colors, icons, legend, pull time, disclaimer, desktop and phone layouts, keyboard focus, contrast, tap targets, reduced-motion behavior, and zoom support.
- Complete the Validation placeholder with one hand-worked case, app results, and match status. Check desktop and phone layouts, resize behavior, loading/error states, reasons-panel behavior, and NWS comparison.

## Added features

### New desktop-only features

2. **Export CSV**
   - Export one row per forecast day and activity (7 days × 3 activities = 21 data rows), preceded by one header row.
   - CSV columns, in this order:
     1. Date (YYYY-MM-DD)
     2. Activity (Crane, Concrete, or Roofing)
     3. Rating (GO, CAUTION, NO-GO, or NO DATA)
     4. Max sustained wind (mph) - Crane rows only, blank otherwise
     5. Max gust (mph) - Crane rows only, blank otherwise
     6. Min temperature (F) - Concrete rows only, blank otherwise
     7. Max rain probability (%) - Roofing rows only, blank otherwise
     8. Limiting variable
     9. Working hours used (for example, 12:00 AM to 11:59 PM)
   - Include units in populated measurement values.
