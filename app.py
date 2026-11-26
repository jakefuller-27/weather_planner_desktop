import tkinter as tk
from tkinter import ttk
import json
import threading
import urllib.request
import ssl
import os
from datetime import datetime

from calc import (
    DEFAULT_LOCATION,
    DAYS,
    STATUS_COLORS,
    STATUS_ICONS,
    build_forecast_url,
    local_day_labels,
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
        self.day_labels = list(DAYS)

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
        ttk.Label(
            header,
            text="Click the map to move the jobsite. Click a calendar cell to see why.",
            style="Hint.TLabel",
        ).pack(anchor="w", pady=(2, 0))

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
                  else f"{latitude:.4f}, {longitude:.4f}"),
            fill="#1E2933",
            font=("TkDefaultFont", 9, "bold"),
            tags="map",
        )

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
            f"{lat:.4f}, {lon:.4f}\n"
            f"{DEFAULT_LOCATION['time_zone']}"
        )
        self.jobsite_label = ttk.Label(jobsite, text=text, justify="left")
        self.jobsite_label.grid(
            row=0, column=0, sticky="w"
        )
        self.refresh_button = ttk.Button(
            jobsite, text="Refresh", state="disabled",
            style="Accent.TButton", command=self.refresh_forecast
        )
        self.refresh_button.grid(row=0, column=1, padx=(10, 0))

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
                values = (
                    "Wind: -- mph\nGust: -- mph"
                    if activity == "Crane"
                    else "Low: -- \u00b0F"
                    if activity == "Concrete"
                    else "Rain: --%"
                )
                self.make_rating_button(
                    grid, status, values, row, column
                )
        self.desktop_calendar = grid

    def make_rating_button(self, parent, status, values, row, column):
        frame = tk.Frame(parent, bg="#FFFFFF", highlightthickness=1,
                         highlightbackground=BORDER)
        frame.grid(row=row, column=column, sticky="nsew", padx=0, pady=0)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        text = f"{STATUS_ICONS[status]}  {status}\n\n{values}"
        foreground = "#202020" if status == "CAUTION" else STATUS_COLORS[status]
        button = tk.Button(
            frame, text=text, fg=foreground, bg="#FFFFFF",
            activebackground="#EDF3F7", activeforeground=foreground,
            relief="flat", bd=0, justify="center",
            font=("TkDefaultFont", 9, "bold"), cursor="hand2",
        )
        button.grid(row=0, column=0, sticky="nsew", ipadx=4, ipady=8)

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

        for day in self.day_labels:
            card = ttk.Frame(inner, style="Card.TFrame", padding=10)
            card.pack(fill="x", padx=4, pady=4)
            ttk.Label(card, text=day, foreground=ACCENT,
                      font=("TkDefaultFont", 10, "bold")).pack(anchor="w")
            for activity, status in (
                ("Crane", "GO"),
                ("Concrete", "GO"),
                ("Roofing", "GO"),
            ):
                values = (
                    "Wind -- mph · Gust -- mph"
                    if activity == "Crane"
                    else "Low -- \u00b0F"
                    if activity == "Concrete"
                    else "Rain --%"
                )
                foreground = "#202020" if status == "CAUTION" else STATUS_COLORS[status]
                tk.Button(
                    card,
                    text=f"{STATUS_ICONS[status]}  {status}   {activity} · {values}",
                    fg=foreground,
                    bg="#FFFFFF",
                    activebackground="#EDF3F7",
                    relief="solid",
                    bd=1,
                    font=("TkDefaultFont", 9),
                    cursor="hand2",
                ).pack(fill="x", pady=3, ipady=5)
        self.phone_calendar = cards

    def build_pull_line(self, parent):
        self.pull_label = ttk.Label(
            parent, text="Forecast pulled at --", foreground=COOL_GRAY
        )
        self.pull_label.grid(
                      row=5, column=0, sticky="w", pady=(8, 4)
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
        ttk.Label(reasons, text="Why this rating?",
                  foreground=ACCENT,
                  font=("TkDefaultFont", 11, "bold")).pack(anchor="w")
        ttk.Label(
            reasons,
            text="Select a calendar cell to see the variables and thresholds.",
            foreground=COOL_GRAY,
        ).pack(anchor="w", pady=(6, 0))

    def build_disclaimer(self, parent):
        disclaimer = ttk.Label(
            parent,
            text=("Ratings are planning aids only, not work authorization. "
                  "Follow your site safety plan, manufacturer limits, and "
                  "applicable codes."),
            foreground="#4D5963",
            background="#EEF2F5",
            wraplength=1080,
            justify="left",
        )
        disclaimer.grid(row=8, column=0, sticky="ew", pady=(14, 0))

    def initial_forecast(self):
        self.fetch_forecast(dict(DEFAULT_LOCATION))

    def refresh_forecast(self):
        self.fetch_forecast(dict(self.selected_location))

    def try_again(self):
        self.fetch_forecast(dict(self.selected_location))

    def fetch_forecast(self, candidate):
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
                    lambda: self.forecast_succeeded(candidate, data),
                )
            except Exception:
                self.after(0, lambda: self.forecast_failed())

        threading.Thread(target=worker, daemon=True).start()

    def forecast_succeeded(self, candidate, data):
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

        time_zone = data.get("timezone", "")
        if not time_zone:
            self.forecast_failed()
            return

        keep_initial_name = candidate["name"] == "West Jordan, UT"
        latitude = candidate["latitude"]
        longitude = candidate["longitude"]
        self.selected_location = {
            "name": ("West Jordan, UT" if keep_initial_name
                     else f"{latitude:.4f}, {longitude:.4f}"),
            "latitude": latitude,
            "longitude": longitude,
            "time_zone": time_zone,
        }
        self.map_center = (latitude, longitude)
        self.forecast_data = data
        self.day_labels = local_day_labels(hourly["time"])

        self.jobsite_label.configure(
            text=(f"{self.selected_location['name']}\n"
                  f"{latitude:.4f}, {longitude:.4f}\n"
                  f"{time_zone}")
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


if __name__ == "__main__":
    app = WeatherPlannerApp()
    app.mainloop()
