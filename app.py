import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import json
import threading
import urllib.request
import ssl
import os
from datetime import datetime
from jobsites import load_jobsite, save_jobsite
from exports import write_forecast_csv

from calc import (
    DEFAULT_LOCATION,
    DAYS,
    STATUS_COLORS,
    STATUS_ICONS,
    RATING_COLORS,
    RATING_ICONS,
    build_forecast_url,
    build_geocoding_url,
    parse_geocoding_results,
    local_day_labels,
    aggregate_daily,
    rate_daily,
)


ACCENT = "#1F4E79"
COOL_GRAY = "#5E6A73"
BORDER = "#CBD4DC"
SURFACE = "#F5F7F9"


class WeatherPlannerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Jobsite Weather Planner")
        self.geometry("1120x820")
        self.minsize(720, 620)
        self.configure(bg="#EEF2F5")

        self.selected_location = dict(DEFAULT_LOCATION)
        self.map_center = (
            DEFAULT_LOCATION["latitude"],
            DEFAULT_LOCATION["longitude"],
        )
        self.forecast_data = None
        self.daily_forecast = []
        self.daily_ratings = []
        self.day_labels = list(DAYS)
        self.valid_start_hour = 0
        self.valid_end_hour = 23 * 60 + 59
        self.working_start_hour = 0
        self.working_end_hour = 23 * 60 + 59
        self.valid_start_label = "12:00 AM"
        self.valid_end_label = "11:59 PM"

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#EEF2F5")
        style.configure("Card.TFrame", background="#FFFFFF", borderwidth=1,
                        relief="solid")
        style.configure("TLabel", background="#FFFFFF", foreground="#1E2933")
        style.configure("Title.TLabel", background="#EEF2F5",
                        foreground=ACCENT, font=("TkDefaultFont", 20, "bold"))
        style.configure("Hint.TLabel", background="#EEF2F5",
                        foreground=COOL_GRAY)
        style.configure("Accent.TButton", font=("TkDefaultFont", 10, "bold"))
        style.configure("Head.TLabel", background=SURFACE, foreground=ACCENT,
                        font=("TkDefaultFont", 10, "bold"),
                        anchor="center", padding=6)
        style.configure("Activity.TLabel", background=SURFACE, foreground=ACCENT,
                        font=("TkDefaultFont", 10, "bold"),
                        anchor="w", padding=(10, 6))

        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        page_canvas = tk.Canvas(self, background="#EEF2F5",
                                highlightthickness=0)
        page_scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=page_canvas.yview
        )
        page_canvas.configure(yscrollcommand=page_scrollbar.set)
        page_canvas.grid(row=0, column=0, sticky="nsew")
        page_scrollbar.grid(row=0, column=1, sticky="ns")

        page = ttk.Frame(page_canvas, padding=16)
        page_window = page_canvas.create_window(
            (0, 0), window=page, anchor="nw"
        )

        def configure_page(event):
            page_canvas.configure(scrollregion=page_canvas.bbox("all"))
            page_canvas.itemconfigure(page_window, width=event.width)

        page_canvas.bind("<Configure>", configure_page)
        page.bind(
            "<Configure>",
            lambda event: page_canvas.configure(
                scrollregion=page_canvas.bbox("all")
            ),
        )
        page_canvas.bind_all(
            "<MouseWheel>",
            lambda event: page_canvas.yview_scroll(
                int(-1 * (event.delta / 120)), "units"
            ),
        )

        container = page
        container.columnconfigure(0, weight=1)

        self.build_header(container)
        self.build_map(container)
        self.build_jobsite(container)
        self.build_status(container)
        self.build_calendar(container)
        self.build_pull_line(container)
        self.build_legend(container)
        self.build_reasons(container)
        self.build_disclaimer(container)

        self.bind("<Configure>", self.on_resize)
        self.after(100, self.initial_forecast)

    def build_header(self, parent):
        header = ttk.Frame(parent)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ttk.Label(header, text="Jobsite Weather Planner",
                  style="Title.TLabel").pack(anchor="w")
        self.hint_label = ttk.Label(
            header,
            text="Click the map to move the jobsite. Click a calendar cell to see why.",
            style="Hint.TLabel",
        )
        self.hint_label.pack(anchor="w", pady=(2, 0))

        search_frame = ttk.Frame(header)
        search_frame.pack(fill="x", pady=(10, 0))
        self.city_search_entry = tk.Entry(
            search_frame, font=("TkDefaultFont", 10),
        )
        self.city_search_entry.insert(0, "Search for a city")
        self.city_search_entry.configure(
            foreground=COOL_GRAY
        )
        self.city_search_entry.bind(
            "<FocusIn>", self.clear_city_placeholder
        )
        self.city_search_entry.bind("<Return>", lambda event: self.search_city())
        self.city_search_entry.pack(side="left", fill="x", expand=True,
                                    ipady=5)
        ttk.Button(search_frame, text="Search",
                   command=self.search_city).pack(
                       side="left", padx=(8, 0), ipadx=8
                   )
        self.city_search_status = ttk.Label(
            header, text="", foreground=COOL_GRAY
        )
        self.city_search_status.pack(anchor="w", pady=(4, 0))
        self.city_search_results = ttk.Frame(header)
        self.city_search_results.pack(fill="x", pady=(4, 0))

    def build_map(self, parent):
        map_card = tk.Frame(parent, bg="#FFFFFF", highlightthickness=1,
                            highlightbackground=BORDER)
        map_card.grid(row=1, column=0, sticky="ew")
        map_card.grid_columnconfigure(0, weight=1)

        self.map_canvas = tk.Canvas(
            map_card, height=230, background="#DDE7ED",
            highlightthickness=0,
        )
        self.map_canvas.grid(row=0, column=0, sticky="ew")
        self.map_canvas.bind("<Button-1>", self.on_map_click)
        self.draw_map()

    def draw_map(self):
        canvas = self.map_canvas
        canvas.delete("map")
        width = max(canvas.winfo_width(), 700)
        height = 230

        canvas.create_rectangle(0, 0, width, height, fill="#DDE7ED",
                                outline="", tags="map")
        canvas.create_rectangle(width * 0.20, 30, width * 0.78, height - 35,
                                fill="#C9DAB9", outline="#A4B494",
                                tags="map")
        canvas.create_line(width * 0.30, 20, width * 0.55, height - 15,
                           fill="#FFFFFF", width=5, tags="map")
        canvas.create_line(width * 0.52, 15, width * 0.48, height - 10,
                           fill="#A7C8E0", width=3, tags="map")

        cx, cy = width * 0.50, height * 0.50
        canvas.create_oval(cx - 9, cy - 9, cx + 9, cy + 9,
                           fill=ACCENT, outline="#FFFFFF", width=2, tags="map")
        latitude = self.selected_location["latitude"]
        longitude = self.selected_location["longitude"]
        canvas.create_text(
            cx, cy - 18,
            text=(self.selected_location["name"]
                  if self.selected_location["name"] == "West Jordan, UT"
                  else f"{latitude:.4f}°, {longitude:.4f}°"),
            fill="#1E2933",
            font=("TkDefaultFont", 9, "bold"),
            tags="map",
        )

    def clear_city_placeholder(self, event):
        if self.city_search_entry.get() == "Search for a city":
            self.city_search_entry.delete(0, "end")
            self.city_search_entry.configure(foreground="#1E2933")

    def parse_hour_label(self, label):
        try:
            text = label.strip()
            meridiem = text[-2:]
            clock = text[:-3].strip()
            hour, minute = (int(part) for part in clock.split(":"))
            if meridiem == "PM" and hour != 12:
                hour += 12
            if meridiem == "AM" and hour == 12:
                hour = 0
            return hour * 60 + minute
        except (ValueError, AttributeError):
            return 0

    def validate_working_hours(self):
        start = self.parse_hour_label(self.start_hour.get())
        end = self.parse_hour_label(self.end_hour.get())
        if end <= start:
            self.hours_validation.configure(
                text="End must be later than Start."
            )
            return
        self.hours_validation.configure(text="")
        self.valid_start_hour = start
        self.valid_end_hour = end
        self.working_start_hour = start
        self.working_end_hour = end
        self.valid_start_label = self.start_hour.get()
        self.valid_end_label = self.end_hour.get()
        self.working_hours_label.configure(
            text=(f"Ratings use working hours "
                  f"{self.start_hour.get()} to {self.end_hour.get()}.")
        )
        self.reaggregate_forecast()

    def reaggregate_forecast(self):
        if not self.forecast_data:
            return
        hourly = self.forecast_data.get("hourly", {})
        self.daily_forecast = aggregate_daily(
            hourly,
            start_hour=self.valid_start_hour // 60,
            end_hour=self.valid_end_hour // 60,
        )
        self.daily_ratings = [
            rate_daily(day) for day in self.daily_forecast
        ]
        self.rebuild_calendar_layout()

    def clear_search_results(self):
        for widget in self.city_search_results.winfo_children():
            widget.destroy()

    def search_city(self):
        query = self.city_search_entry.get().strip()
        if query == "Search for a city":
            query = ""
        self.clear_search_results()
        if len(query) < 2:
            self.city_search_status.configure(
                text="Enter at least 2 characters.",
                foreground=STATUS_COLORS["NO-GO"],
            )
            return

        self.city_search_status.configure(
            text="Searching...", foreground=ACCENT
        )

        def worker():
            try:
                url = build_geocoding_url(query)
                context = ssl.create_default_context()
                for ca_bundle in (
                    "/etc/ssl/cert.pem",
                    "/Library/Frameworks/Python.framework/Versions/3.15/etc/openssl/cert.pem",
                ):
                    if os.path.isfile(ca_bundle):
                        context = ssl.create_default_context(cafile=ca_bundle)
                        break
                request = urllib.request.Request(
                    url, headers={"Accept": "application/json"}
                )
                with urllib.request.urlopen(
                        request, timeout=15, context=context) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                matches = parse_geocoding_results(payload)
                self.after(0, lambda: self.show_city_matches(matches))
            except Exception:
                self.after(0, lambda: self.show_city_search_error())

        threading.Thread(target=worker, daemon=True).start()

    def show_city_matches(self, matches):
        self.clear_search_results()
        if not matches:
            self.city_search_status.configure(
                text="No matches found.", foreground=COOL_GRAY
            )
            return
        self.city_search_status.configure(text="", foreground=COOL_GRAY)
        for match in matches:
            name = match["name"]
            region = match["admin1"]
            country = match["country"]
            label = ", ".join(
                part for part in (name, region, country) if part
            )
            ttk.Button(
                self.city_search_results,
                text=label,
                command=lambda m=match: self.select_city_match(m),
            ).pack(fill="x", pady=2)

    def show_city_search_error(self):
        self.clear_search_results()
        self.city_search_status.configure(
            text="Search failed. Try again.",
            foreground=STATUS_COLORS["NO-GO"],
        )

    def select_city_match(self, match):
        candidate = {
            "name": match["name"],
            "latitude": match["latitude"],
            "longitude": match["longitude"],
            "time_zone": "",
        }
        self.clear_search_results()
        self.city_search_status.configure(text="", foreground=COOL_GRAY)
        self.fetch_forecast(candidate)

    def on_map_click(self, event):
        canvas = self.map_canvas
        width = max(canvas.winfo_width(), 700)
        longitude = ((event.x / width) * 360) - 180
        height = 230
        latitude = 90 - ((event.y / height) * 180)
        latitude = max(-90.0, min(90.0, latitude))
        longitude = max(-180.0, min(180.0, longitude))
        candidate = {
            "name": f"{latitude:.4f}, {longitude:.4f}",
            "latitude": latitude,
            "longitude": longitude,
            "time_zone": "",
        }
        self.fetch_forecast(candidate)

    def build_jobsite(self, parent):
        jobsite = ttk.Frame(parent, style="Card.TFrame", padding=10)
        jobsite.grid(row=2, column=0, sticky="ew", pady=(8, 12))
        jobsite.columnconfigure(0, weight=1)

        lat = DEFAULT_LOCATION["latitude"]
        lon = DEFAULT_LOCATION["longitude"]
        text = (
            f"{DEFAULT_LOCATION['name']}\n"
            f"Latitude: {lat:.4f}°, Longitude: {lon:.4f}°\n"
            f"Time zone: {DEFAULT_LOCATION['time_zone']}"
        )
        self.jobsite_label = ttk.Label(jobsite, text=text, justify="left")
        self.jobsite_label.grid(
            row=0, column=0, sticky="w"
        )
        actions = ttk.Frame(jobsite)
        actions.grid(row=1, column=0, columnspan=5, sticky="w", pady=(8, 0))
        self.refresh_button = ttk.Button(
            actions, text="Refresh forecast", state="disabled",
            style="Accent.TButton", command=self.refresh_forecast
        )
        self.refresh_button.pack(side="left", padx=(0, 8))
        ttk.Button(
            actions, text="Save jobsite", command=self.save_current_jobsite
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            actions, text="Open jobsite", command=self.open_saved_jobsite
        ).pack(side="left", padx=(0, 8))
        ttk.Button(
            actions, text="Export CSV", command=self.export_csv
        ).pack(side="left")

        hours = (
            "12:00 AM", "1:00 AM", "2:00 AM", "3:00 AM",
            "4:00 AM", "5:00 AM", "6:00 AM", "7:00 AM",
            "8:00 AM", "9:00 AM", "10:00 AM", "11:00 AM",
            "12:00 PM", "1:00 PM", "2:00 PM", "3:00 PM",
            "4:00 PM", "5:00 PM", "6:00 PM", "7:00 PM",
            "8:00 PM", "9:00 PM", "10:00 PM", "11:00 PM",
            "11:59 PM",
        )
        hours_frame = ttk.Frame(jobsite)
        hours_frame.grid(row=2, column=0, columnspan=5,
                         sticky="w", pady=(8, 0))
        ttk.Label(hours_frame, text="Start time").pack(side="left")
        self.start_hour = ttk.Combobox(
            hours_frame, values=hours, state="readonly", width=10
        )
        self.start_hour.set("12:00 AM")
        self.start_hour.pack(side="left", padx=(5, 12))
        ttk.Label(hours_frame, text="End time").pack(side="left")
        self.end_hour = ttk.Combobox(
            hours_frame, values=hours, state="readonly", width=10
        )
        self.end_hour.set("11:59 PM")
        self.end_hour.pack(side="left", padx=(5, 0))
        self.start_hour.bind("<<ComboboxSelected>>",
                             lambda event: self.validate_working_hours())
        self.end_hour.bind("<<ComboboxSelected>>",
                           lambda event: self.validate_working_hours())
        self.hours_validation = ttk.Label(
            hours_frame, text="", foreground=STATUS_COLORS["NO-GO"]
        )
        self.hours_validation.pack(side="left", padx=(12, 0))

    def build_status(self, parent):
        status = ttk.Frame(parent)
        status.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        status.columnconfigure(0, weight=1)
        self.loading_label = ttk.Label(
            status, text="Loading forecast...", foreground=ACCENT
        )
        self.loading_label.grid(row=0, column=0, sticky="w")
        self.error_label = ttk.Label(
            status, text="Could not load the forecast.",
            foreground=STATUS_COLORS["NO-GO"]
        )
        self.error_label.grid(row=0, column=1, padx=10, sticky="e")
        self.try_again_button = ttk.Button(
            status, text="Try again", state="disabled",
            command=self.try_again
        )
        self.try_again_button.grid(
            row=0, column=2, sticky="e"
        )
        self.error_label.grid_remove()
        self.try_again_button.grid_remove()

    def build_calendar(self, parent):
        self.calendar_host = ttk.Frame(parent)
        self.calendar_host.grid(row=4, column=0, sticky="nsew")
        self.desktop_calendar = None
        self.phone_calendar = None
        self.update_layout()

    def update_layout(self):
        if self.winfo_width() >= 920:
            self.show_desktop_calendar()
        else:
            self.show_phone_cards()

    def rebuild_calendar_layout(self):
        if self.desktop_calendar is not None:
            self.desktop_calendar.destroy()
            self.desktop_calendar = None
        if self.phone_calendar is not None:
            self.phone_calendar.destroy()
            self.phone_calendar = None
        self.update_layout()

    def show_desktop_calendar(self):
        if self.desktop_calendar is not None:
            return
        if self.phone_calendar is not None:
            self.phone_calendar.destroy()
            self.phone_calendar = None

        grid = ttk.Frame(self.calendar_host)
        grid.pack(fill="both", expand=True)
        for column in range(8):
            grid.columnconfigure(column, weight=1)

        ttk.Label(grid, text="Activity", style="Head.TLabel",
                  borderwidth=1, relief="solid").grid(
                      row=0, column=0, sticky="nsew"
                  )
        for column, day in enumerate(self.day_labels, start=1):
            ttk.Label(grid, text=day, style="Head.TLabel",
                      borderwidth=1, relief="solid").grid(
                          row=0, column=column, sticky="nsew"
                      )

        activities = ("Crane", "Concrete", "Roofing")
        mock_statuses = (
            ("GO", "CAUTION", "NO-GO", "NO DATA",
             "GO", "CAUTION", "NO-GO"),
            ("GO", "CAUTION", "NO-GO", "GO",
             "CAUTION", "NO DATA", "GO"),
            ("GO", "CAUTION", "NO-GO", "GO",
             "CAUTION", "NO DATA", "GO"),
        )
        for row, (activity, statuses) in enumerate(
                zip(activities, mock_statuses), start=1):
            ttk.Label(grid, text=activity, style="Activity.TLabel",
                      borderwidth=1, relief="solid").grid(
                          row=row, column=0, sticky="nsew"
                      )
            for column, status in enumerate(statuses, start=1):
                day_index = column - 1
                if day_index < len(self.daily_ratings):
                    key = activity.lower()
                    rating_data = self.daily_ratings[day_index][key]
                    status = rating_data["rating"]
                    day = self.daily_forecast[day_index]
                else:
                    rating_data = None
                    day = None
                values = (
                    "Wind: -- mph\nGust: -- mph"
                    if activity == "Crane"
                    else "Low: -- \u00b0F"
                    if activity == "Concrete"
                    else "Rain: --%"
                )
                if rating_data is not None:
                    if activity == "Crane":
                        values = (
                            f"Wind: {rating_data['wind'] if rating_data['wind'] is not None else '--'} mph\n"
                            f"Gust: {rating_data['gust'] if rating_data['gust'] is not None else '--'} mph"
                        )
                    elif activity == "Concrete":
                        values = f"Low: {rating_data['temperature'] if rating_data['temperature'] is not None else '--'} \u00b0F"
                    else:
                        values = f"Rain: {rating_data['rain'] if rating_data['rain'] is not None else '--'}%"
                self.make_rating_label(
                    grid, status, values, row, column,
                    activity=activity, day=day, rating_data=rating_data
                )
        self.desktop_calendar = grid

    def make_rating_label(self, parent, status, values, row, column,
                          activity=None, day=None, rating_data=None):
        icon = RATING_ICONS.get(status, STATUS_ICONS[status])
        text = f"{icon}  {status}\n\n{values}"
        foreground = "#202020" if status == "CAUTION" else "#FFFFFF"
        callback = lambda: self.open_reasons(activity, day, rating_data)
        label = tk.Label(
            parent,
            text=text,
            fg=foreground,
            bg=RATING_COLORS[status],
            activeforeground=foreground,
            activebackground=RATING_COLORS[status],
            relief="solid",
            bd=1,
            justify="center",
            anchor="center",
            font=("TkDefaultFont", 9, "bold"),
            cursor="hand2",
            takefocus=True,
            wraplength=125,
            padx=4,
            pady=8,
            highlightthickness=0,
        )
        label.grid(row=row, column=column, sticky="nsew")
        label.bind(
            "<Configure>",
            lambda event, widget=label: widget.configure(
                wraplength=max(52, event.width - 10)
            ),
        )
        label.bind("<Button-1>", lambda event: callback())
        label.bind("<Return>", lambda event: callback())
        label.bind("<space>", lambda event: callback())
        label.bind(
            "<FocusIn>",
            lambda event: label.configure(
                highlightthickness=2, highlightbackground=ACCENT,
                highlightcolor=ACCENT
            ),
        )
        label.bind(
            "<FocusOut>",
            lambda event: label.configure(highlightthickness=0),
        )

    def show_phone_cards(self):
        if self.phone_calendar is not None:
            return
        if self.desktop_calendar is not None:
            self.desktop_calendar.destroy()
            self.desktop_calendar = None

        cards = ttk.Frame(self.calendar_host)
        cards.pack(fill="both", expand=True)
        canvas = tk.Canvas(cards, background="#EEF2F5", highlightthickness=0)
        scrollbar = ttk.Scrollbar(cards, orient="vertical",
                                  command=canvas.yview)
        inner = ttk.Frame(canvas)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        canvas.create_window((0, 0), window=inner, anchor="nw")
        inner.bind(
            "<Configure>",
            lambda event: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        for day_index, day in enumerate(self.day_labels):
            card = ttk.Frame(inner, style="Card.TFrame", padding=10)
            card.pack(fill="x", padx=4, pady=4)
            ttk.Label(card, text=day, foreground=ACCENT,
                      font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
            for activity in ("Crane", "Concrete", "Roofing"):
                status = "GO"
                rating_data = None
                day_data = None
                if day_index < len(self.daily_ratings):
                    rating_data = self.daily_ratings[day_index][activity.lower()]
                    status = rating_data["rating"]
                    day_data = self.daily_forecast[day_index]
                values = (
                    "Wind -- mph · Gust -- mph"
                    if activity == "Crane"
                    else "Low -- \u00b0F"
                    if activity == "Concrete"
                    else "Rain --%"
                )
                if rating_data is not None:
                    if activity == "Crane":
                        values = (
                            f"Wind {rating_data['wind'] if rating_data['wind'] is not None else '--'} mph · "
                            f"Gust {rating_data['gust'] if rating_data['gust'] is not None else '--'} mph"
                        )
                    elif activity == "Concrete":
                        values = f"Low {rating_data['temperature'] if rating_data['temperature'] is not None else '--'} \u00b0F"
                    else:
                        values = f"Rain {rating_data['rain'] if rating_data['rain'] is not None else '--'}%"
                foreground = "#202020" if status == "CAUTION" else "#FFFFFF"
                label = tk.Label(
                    card,
                    text=f"{RATING_ICONS[status]}  {status}   {activity} · {values}",
                    fg=foreground,
                    bg=RATING_COLORS[status],
                    relief="solid",
                    bd=1,
                    font=("TkDefaultFont", 9, "bold"),
                    cursor="hand2",
                    takefocus=True,
                    anchor="w",
                    justify="left",
                    wraplength=620,
                    padx=10,
                    pady=8,
                    highlightthickness=0,
                )
                label.pack(fill="x", pady=3)
                label.bind(
                    "<Configure>",
                    lambda event, widget=label: widget.configure(
                        wraplength=max(120, event.width - 24)
                    ),
                )
                callback = (
                    lambda a=activity, d=day_data, r=rating_data:
                    self.open_reasons(a, d, r)
                )
                label.bind("<Button-1>", lambda event, cb=callback: cb())
                label.bind("<Return>", lambda event, cb=callback: cb())
                label.bind("<space>", lambda event, cb=callback: cb())
                label.bind(
                    "<FocusIn>",
                    lambda event, widget=label: widget.configure(
                        highlightthickness=2, highlightbackground=ACCENT,
                        highlightcolor=ACCENT
                    ),
                )
                label.bind(
                    "<FocusOut>",
                    lambda event, widget=label: widget.configure(
                        highlightthickness=0
                    ),
                )
        self.phone_calendar = cards

    def build_pull_line(self, parent):
        self.pull_label = ttk.Label(
            parent, text="Forecast pulled at --", foreground=COOL_GRAY
        )
        self.pull_label.grid(
                      row=5, column=0, sticky="w", pady=(8, 4)
                  )
        self.working_hours_label = ttk.Label(
            parent,
            text="Ratings use working hours 12:00 AM to 11:59 PM",
            foreground=COOL_GRAY,
        )
        self.working_hours_label.grid(
            row=5, column=0, sticky="w", pady=(30, 4)
        )

    def build_legend(self, parent):
        legend = ttk.Frame(parent, style="Card.TFrame", padding=10)
        legend.grid(row=6, column=0, sticky="ew", pady=(6, 8))
        for status in ("GO", "CAUTION", "NO-GO", "NO DATA"):
            foreground = "#806000" if status == "CAUTION" else STATUS_COLORS[status]
            ttk.Label(
                legend,
                text=f"{STATUS_ICONS[status]}  {status}",
                foreground=foreground,
                font=("TkDefaultFont", 9, "bold"),
            ).pack(side="left", padx=(0, 18))

    def build_reasons(self, parent):
        reasons = ttk.Frame(parent, style="Card.TFrame", padding=12)
        reasons.grid(row=7, column=0, sticky="ew")
        self.reasons_title = ttk.Label(
            reasons, text="Why this rating?",
            foreground=ACCENT, font=("TkDefaultFont", 11, "bold")
        )
        self.reasons_title.pack(anchor="w")
        self.reasons_text = ttk.Label(
            reasons,
            text="Select a calendar cell to see the variables and thresholds.",
            foreground=COOL_GRAY,
            justify="left",
            wraplength=900,
        )
        self.reasons_text.pack(anchor="w", pady=(6, 0))

    def open_reasons(self, activity, day, rating_data):
        if activity is None or day is None or rating_data is None:
            return
        date = day["date"]
        rating = rating_data["rating"]
        if activity == "Crane":
            wind = rating_data["wind"]
            gust = rating_data["gust"]
            lines = [
                f"Activity: Crane",
                f"Date: {date}",
                f"Rating: {rating}",
                f"Sustained wind: {wind if wind is not None else '--'} mph "
                f"(GO < 15 mph; CAUTION 15 to <20 mph; NO-GO >=20 mph)"
                f"{' at ' + rating_data['wind_time'] if rating_data['wind_time'] else ''}",
                f"Gust: {gust if gust is not None else '--'} mph "
                "(GO < 20 mph; CAUTION 20 to <25 mph; NO-GO >=25 mph)"
                f"{' at ' + rating_data['gust_time'] if rating_data['gust_time'] else ''}",
                f"Limiting variable: {rating_data['limiting']}",
                "Wind is forecast at 10 m above ground and likely understates wind at boom height. "
                "Always follow the crane manufacturer's limits and site wind readings.",
            ]
        elif activity == "Concrete":
            temperature = rating_data["temperature"]
            lines = [
                f"Activity: Concrete",
                f"Date: {date}",
                f"Rating: {rating}",
                f"Minimum temperature: {temperature if temperature is not None else '--'} °F "
                "(GO >=40 °F; CAUTION 32 to <40 °F; NO-GO <32 °F)"
                f"{' at ' + rating_data['time'] if rating_data['time'] else ''}",
                f"Limiting variable: {rating_data['limiting']}",
            ]
        else:
            rain = rating_data["rain"]
            lines = [
                f"Activity: Roofing",
                f"Date: {date}",
                f"Rating: {rating}",
                f"Maximum rain probability: {rain if rain is not None else '--'}% "
                "(GO <20%; CAUTION 20 to <50%; NO-GO >=50%)"
                f"{' at ' + rating_data['time'] if rating_data['time'] else ''}",
                f"Limiting variable: {rating_data['limiting']}",
            ]
        lines.append(
            f"Working hours: {self.start_hour.get()} to {self.end_hour.get()}"
        )
        self.reasons_title.configure(
            text=f"{RATING_ICONS[rating]}  {activity}: {rating}"
        )
        self.reasons_text.configure(text="\n".join(lines))

    def build_disclaimer(self, parent):
        self.disclaimer_label = ttk.Label(
            parent,
            text=("Ratings are planning aids only, not work authorization. "
                  "Follow your site safety plan, manufacturer limits, and "
                  "applicable codes."),
            foreground="#4D5963",
            background="#EEF2F5",
            wraplength=900,
            justify="left",
        )
        self.disclaimer_label.grid(row=8, column=0, sticky="ew", pady=(14, 0))

    def initial_forecast(self):
        self.fetch_forecast(dict(DEFAULT_LOCATION))

    def save_current_jobsite(self):
        path = filedialog.asksaveasfilename(
            title="Save jobsite",
            defaultextension=".json",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
        )
        if not path:
            return
        payload = {
            "jobsite_name": self.selected_location["name"],
            "latitude": self.selected_location["latitude"],
            "longitude": self.selected_location["longitude"],
            "time_zone": self.selected_location["time_zone"],
            "start_hour": self.valid_start_label,
            "end_hour": self.valid_end_label,
        }
        try:
            save_jobsite(path, payload)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Could not save jobsite", str(exc), parent=self)
            return
        messagebox.showinfo(
            "Jobsite saved", "The jobsite was saved successfully.", parent=self
        )

    def open_saved_jobsite(self):
        path = filedialog.askopenfilename(
            title="Open jobsite",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
        )
        if not path:
            return
        try:
            saved = load_jobsite(path)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError, ValueError) as exc:
            messagebox.showerror(
                "Could not open jobsite",
                f"The selected file is invalid or unavailable.\n\n{exc}",
                parent=self,
            )
            return

        candidate = {
            "name": saved["jobsite_name"],
            "latitude": saved["latitude"],
            "longitude": saved["longitude"],
            "time_zone": saved["time_zone"],
        }
        self.fetch_forecast(candidate, pending_jobsite=saved)

    def export_csv(self):
        if not self.forecast_data:
            messagebox.showerror(
                "Forecast unavailable",
                "Load a forecast before exporting CSV.",
                parent=self,
            )
            return
        path = filedialog.asksaveasfilename(
            title="Export forecast CSV",
            defaultextension=".csv",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if not path:
            return
        try:
            row_count = write_forecast_csv(
                path,
                self.daily_forecast,
                self.daily_ratings,
                self.valid_start_label,
                self.valid_end_label,
            )
        except (OSError, ValueError, KeyError) as exc:
            messagebox.showerror(
                "Could not export CSV", str(exc), parent=self
            )
            return
        messagebox.showinfo(
            "CSV exported",
            f"Exported {row_count} activity rows.",
            parent=self,
        )

    def refresh_forecast(self):
        self.fetch_forecast(dict(self.selected_location))

    def try_again(self):
        self.fetch_forecast(dict(self.selected_location))

    def fetch_forecast(self, candidate, pending_jobsite=None):
        self.loading_label.grid(row=0, column=0, sticky="w")
        self.error_label.grid_remove()
        self.try_again_button.grid_remove()
        self.calendar_host.grid_remove()
        self.refresh_button.configure(state="disabled")

        def worker():
            url = build_forecast_url(
                candidate["latitude"], candidate["longitude"]
            )
            try:
                request = urllib.request.Request(
                    url,
                    headers={"Accept": "application/json"},
                )
                ssl_context = ssl.create_default_context()
                for ca_bundle in (
                    "/etc/ssl/cert.pem",
                    "/Library/Frameworks/Python.framework/Versions/3.15/etc/openssl/cert.pem",
                ):
                    if os.path.isfile(ca_bundle):
                        ssl_context = ssl.create_default_context(
                            cafile=ca_bundle
                        )
                        break
                with urllib.request.urlopen(
                        request, timeout=15, context=ssl_context) as response:
                    data = json.loads(response.read().decode("utf-8"))
                self.after(
                    0,
                    lambda: self.forecast_succeeded(
                        candidate, data, pending_jobsite
                    ),
                )
            except Exception:
                self.after(0, lambda: self.forecast_failed())

        threading.Thread(target=worker, daemon=True).start()

    def forecast_succeeded(self, candidate, data, pending_jobsite=None):
        hourly = data.get("hourly", {})
        required = (
            "time",
            "temperature_2m",
            "wind_speed_10m",
            "wind_gusts_10m",
            "precipitation_probability",
        )
        if not isinstance(hourly, dict) or not all(
                key in hourly for key in required):
            self.forecast_failed()
            return

        api_time_zone = data.get("timezone", "")
        if not api_time_zone:
            self.forecast_failed()
            return
        time_zone = (
            pending_jobsite["time_zone"]
            if pending_jobsite is not None
            else api_time_zone
        )
        if not time_zone:
            self.forecast_failed()
            return

        keep_initial_name = candidate["name"] == "West Jordan, UT"
        latitude = candidate["latitude"]
        longitude = candidate["longitude"]
        self.selected_location = {
            "name": ("West Jordan, UT" if keep_initial_name
                     else candidate["name"]),
            "latitude": latitude,
            "longitude": longitude,
            "time_zone": time_zone,
        }
        if pending_jobsite is not None:
            self.valid_start_hour = pending_jobsite["start_hour_value"]
            self.valid_end_hour = pending_jobsite["end_hour_value"]
            self.working_start_hour = self.valid_start_hour
            self.working_end_hour = self.valid_end_hour
            self.valid_start_label = pending_jobsite["start_hour"]
            self.valid_end_label = pending_jobsite["end_hour"]
            self.start_hour.set(pending_jobsite["start_hour"])
            self.end_hour.set(pending_jobsite["end_hour"])
            self.hours_validation.configure(text="")
            self.working_hours_label.configure(
                text=(f"Ratings use working hours "
                      f"{pending_jobsite['start_hour']} to "
                      f"{pending_jobsite['end_hour']}.")
            )
        self.map_center = (latitude, longitude)
        self.forecast_data = data
        self.daily_forecast = aggregate_daily(
            hourly,
            start_hour=self.valid_start_hour // 60,
            end_hour=self.valid_end_hour // 60,
        )
        self.daily_ratings = [
            rate_daily(day) for day in self.daily_forecast
        ]
        self.day_labels = local_day_labels(hourly["time"])

        self.jobsite_label.configure(
            text=(f"{self.selected_location['name']}\n"
                  f"Latitude: {latitude:.4f}°, "
                  f"Longitude: {longitude:.4f}°\n"
                  f"Time zone: {time_zone}")
        )
        now = datetime.now().astimezone()
        hour = now.strftime("%I").lstrip("0") or "0"
        pull_time = now.strftime(f"%A, %B %d, %Y at {hour}:%M %p")
        self.pull_label.configure(text=f"Forecast pulled at {pull_time}")

        self.loading_label.grid_remove()
        self.error_label.grid_remove()
        self.try_again_button.grid_remove()
        self.calendar_host.grid(row=4, column=0, sticky="nsew")
        self.refresh_button.configure(state="normal")
        self.rebuild_calendar_layout()
        self.draw_map()

    def forecast_failed(self):
        self.loading_label.grid_remove()
        self.error_label.grid()
        self.try_again_button.configure(state="normal")
        self.try_again_button.grid(row=0, column=2, sticky="e")
        self.refresh_button.configure(state="normal")
        if self.forecast_data is None:
            self.calendar_host.grid_remove()
        else:
            self.calendar_host.grid(row=4, column=0, sticky="nsew")

    def on_resize(self, event):
        if event.widget is self:
            self.draw_map()
            self.update_layout()
            wraplength = max(320, self.winfo_width() - 64)
            self.hint_label.configure(wraplength=wraplength)
            self.jobsite_label.configure(wraplength=wraplength)
            self.reasons_text.configure(wraplength=wraplength)
            self.disclaimer_label.configure(wraplength=wraplength)


if __name__ == "__main__":
    app = WeatherPlannerApp()
    app.mainloop()
