import customtkinter as ctk
import tkinter as tk  # Import standard tkinter for scrollbar
import json
import time
import threading
import signal
import sys
from queue import Queue
import logging
import first_site
import second_site  # Import the crawler module
import os
import hard_json
import hyperSel
import webbrowser  # For opening links in the default browser

# Constants for pagination
BATCH_SIZE = 20
SCROLL_THRESHOLD = 0.8  # Load more data when scrollbar is within 20% of the bottom

# Set up logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def clean_entry(entry):
    """Cleans an entry by removing newlines, tabs, and leading/trailing spaces from each string field."""
    for key, value in entry.items():
        if isinstance(value, str):
            entry[key] = value.replace("\n", "").replace("\t", "").strip()
    return entry

def load_crawl_data(filepath="./logs/crawl_data.json"):
    """Loads data from a JSON file and combines it with hardcoded data."""
    combined_data = []
    city_addr_pairs = []
    dupes = 0
    # Add hardcoded data
    for entry in hard_json.data_json_hardcoded:
        entry = clean_entry(entry)  # Clean the entry
        city = entry['city']
        addr = entry['address1']

        pair = [city, addr]

        if pair not in city_addr_pairs:
            combined_data.append(entry)
            city_addr_pairs.append(pair)
        else:
            dupes+=1

    # Add data from the file if it exists
    if os.path.exists(filepath) and os.path.getsize(filepath) > 0:
        with open(filepath, "r") as file:
            try:
                file_data = json.load(file)
                if isinstance(file_data, list):
                    for entry in file_data:
                        entry = clean_entry(entry)  # Clean the entry
                        city = entry['city']
                        addr = entry['address1']

                        pair = [city, addr]
                        if pair not in city_addr_pairs:
                            combined_data.append(entry)
                            city_addr_pairs.append(pair)
                        else:
                            dupes+=1
                else:
                    print("Warning: JSON data in file is not a list.")
            except json.JSONDecodeError:
                print("Warning: JSON decoding failed. Using only hardcoded data.")

    print("combined_data:", len(combined_data))
    print("dupes", dupes)
    return combined_data

# Initialize the main application window
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self, shutdown_event):
        super().__init__()
        self.title("License Data Viewer")
        self.geometry("1500x600")
        self.shutdown_event = shutdown_event  # Event for controlled shutdown
        self.progress_queue = Queue()
        
        # Configure grid for resizing
        self.columnconfigure(0, weight=2)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        self.rowconfigure(1, weight=1)
        
        # Initialize and load data
        self.crawl_data = load_crawl_data()
        self.filtered_data = self.crawl_data  # Use crawl_data directly without initial filtering
        self.display_data = []  # Stores currently displayed data
        self.current_batch = 0  # Track the current batch for pagination
        self.sort_order = {  # Default sort order (None: unsorted, True: ascending, False: descending)
            "owner_name": None,
            "license_number": None,
            "business_type": None,
            "expiration_date": None
        }
        
        # Set up GUI elements (search bar, data display, filters, buttons, etc.)
        self.setup_ui()
        self.load_data()  # Load the initial batch of data

        # Start crawl thread in the background, set as daemon
        self.crawl_thread = threading.Thread(target=self.start_crawl, daemon=True)
        self.crawl_thread.start()

        # Monitor the queue for crawl progress
        self.after(100, self.simulate_crawl)

    def setup_ui(self):
        """Sets up the main UI elements."""
        # Search and Filter Section
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(self, textvariable=self.search_var, width=600, placeholder_text="Search by name")
        self.search_entry.grid(row=0, column=0, padx=20, pady=20, columnspan=2, sticky="ew")
        
        self.search_button = ctk.CTkButton(self, text="Search", command=self.search, width=100)
        self.search_button.grid(row=0, column=2, padx=10, pady=20, sticky="e")
        
        # Data Display Frame with Scrollbar
        self.scrollbar = tk.Scrollbar(self, orient="vertical")
        self.scrollbar.grid(row=1, column=2, sticky="ns", padx=(0, 10))

        self.data_frame = ctk.CTkScrollableFrame(self, width=700, height=400)
        self.data_frame.grid(row=1, column=0, columnspan=2, padx=20, pady=10, sticky="nsew")
        self.scrollbar.config(command=self.data_frame._parent_canvas.yview)
        self.data_frame._parent_canvas.config(yscrollcommand=self.scrollbar.set)
        self.data_frame.bind("<MouseWheel>", self.on_scroll)

        # Side HUD Panel
        self.hud_frame = ctk.CTkFrame(self, width=280, height=400)
        self.hud_frame.grid(row=1, column=3, padx=20, pady=10, sticky="ns")

        # HUD Filters for missing data
        #self.total_data_label = ctk.CTkLabel(self.hud_frame, text=f"TOTAL DATA: {len(self.crawl_data)}", font=("Arial", 14, "bold"))
        #self.total_data_label.pack(pady=(20, 10))

        # Filter checkboxes with default values (expiration_date ON, others OFF)
        self.filter_vars = {
            "expiration_date": ctk.BooleanVar(value=True),
            "business_type": ctk.BooleanVar(value=False),
            "license_number": ctk.BooleanVar(value=False),
            "owner_name": ctk.BooleanVar(value=False)
        }

        # Filter checkboxes
        for field, var in self.filter_vars.items():
            ctk.CTkCheckBox(
                self.hud_frame, text=f"Needs {field.replace('_', ' ').title()}",
                variable=var, command=self.apply_filters
            ).pack(pady=(5, 5))

        # Sorting options with up/down toggle buttons for each sortable field
        for field in ["owner_name", "license_number", "business_type", "expiration_date"]:
            sort_frame = ctk.CTkFrame(self.hud_frame)
            sort_frame.pack(pady=(5, 5), fill="x")
            
            sort_label = ctk.CTkLabel(sort_frame, text=field.replace('_', ' ').title(), font=("Arial", 12))
            sort_label.pack(side="left", padx=(10, 5))
            
            # Up (ascending) and Down (descending) sorting buttons
            up_button = ctk.CTkButton(sort_frame, text="↑", width=20, command=lambda f=field: self.sort_data(f, True))
            down_button = ctk.CTkButton(sort_frame, text="↓", width=20, command=lambda f=field: self.sort_data(f, False))
            up_button.pack(side="left", padx=(5, 5))
            down_button.pack(side="left")

        # Progress bar setup
        self.progress_frame = ctk.CTkFrame(self, width=280, height=400)
        self.progress_frame.grid(row=1, column=4, padx=20, pady=10, sticky="ns")
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, width=250)
        self.progress_bar.grid(row=0, column=0, padx=20, pady=(30, 10))
        self.progress_label = ctk.CTkLabel(self.progress_frame, text="Automatic Beginning Second Site Crawl..", font=("Arial", 12, "bold"))
        self.progress_label.grid(row=1, column=0, pady=(10, 0))
        self.progress_label2 = ctk.CTkLabel(self.progress_frame, text="Begin First Site Crawl?", font=("Arial", 12, "bold"))
        self.progress_label2.grid(row=3, column=0, pady=(10, 0))
        
        self.time_label = ctk.CTkLabel(self.progress_frame, text="Time elapsed: 0s", font=("Arial", 12))
        self.time_label.grid(row=2, column=0, pady=(10, 20))

        # "Run First Crawler" button
        self.first_crawler_button = ctk.CTkButton(
            self.progress_frame,
            text="Run First Crawler",
            command=self.run_first_crawler
        )
        self.first_crawler_button.grid(row=4, column=0, padx=20, pady=(20, 0))

    def sort_data(self, field, ascending):
        """Sorts data based on the specified field and order, treating None as empty strings for comparison."""
        self.filtered_data.sort(
            key=lambda x: (x.get(field) is None, x.get(field, "")),  # Sorts None values to the end
            reverse=not ascending
        )
        self.current_batch = 0
        self.load_data()
        # Update sort order to keep track
        self.sort_order[field] = ascending

    def run_first_crawler(self):
        """Starts the first crawler and updates the button text/status."""
        self.first_crawler_button.configure(state="disabled", text="Running first crawler...")
        self.progress_label2.configure(text="Running first crawler...")

        def start_crawler():
            first_site.main()  # Start the first crawler
            self.first_crawler_button.configure(state="normal", text="Run First Crawler")
            self.progress_label2.configure(text="Finished first crawler")

        # Run the first crawler in a background thread
        threading.Thread(target=start_crawler, daemon=True).start()

    def start_crawl(self):
        second_site.main(self.progress_queue)

    def simulate_crawl(self):
        """Updates the progress bar based on the progress from second_site."""
        start_time = time.time()
        try:
            while not self.progress_queue.empty():
                progress = self.progress_queue.get()
                self.progress_bar.set(progress)
                time_elapsed = int(time.time() - start_time)
                self.time_label.configure(text=f"30-60 minutes to complete...")
                self.progress_label.configure(text=f"Second Crawler running... {int((progress * 100) +1)}%")

                if progress >= 1.0:
                    self.progress_label.configure(text="Done Second Crawler")
                    return
            self.after(100, self.simulate_crawl)
        except Exception as e:
            print(f"Error in simulate_crawl: {e}")
            self.progress_label.configure(text="Error occurred during crawl")

    def apply_filters(self):
        logging.info("Applying filters to data.")
        filtered_data = []
        count = {"1":0, "2":0, "3":0,"4":0,  "good":0}
        for entry in self.crawl_data:
            exclude = False
            for field, var in self.filter_vars.items():
                if not var.get():
                    continue

                item = entry.get(field)
                if item == "":
                    count['1'] +=1
                    exclude = True
                    break
        
                if item == "n/a" or item == "N/A":
                    count['4'] +=1
                    exclude = True
                    break

                if item == None:
                    count['2'] +=1
                    exclude = True
                    break

                if item == "null":
                    count['3'] +=1
                    exclude = True
                    break

            if not exclude:
                count['good'] +=1
                filtered_data.append(entry)

        self.filtered_data = filtered_data
        self.current_batch = 0  # Reset pagination for new filtered data
        logging.info(f"Number of entries after filtering: {len(self.filtered_data)}")
        self.load_data()

    def load_data(self, append=False):
        start_index = self.current_batch * BATCH_SIZE
        end_index = start_index + BATCH_SIZE
        visible_batch = self.filtered_data[start_index:end_index]

        if not append:
            for widget in self.data_frame.winfo_children():
                widget.destroy()
            self.display_data = []

        colors = ["#2E2E2E", "#393939"]

        for index, entry in enumerate(visible_batch):
            entry_frame = ctk.CTkFrame(self.data_frame, corner_radius=10, fg_color=colors[(index + len(self.display_data)) % 2])
            entry_frame.pack(fill="x", padx=5, pady=5)
            
            name_label = ctk.CTkLabel(entry_frame, text=f"Name: {entry.get('owner_name', 'N/A')}", font=("Arial", 14, "bold"))
            name_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

            location_label = ctk.CTkLabel(entry_frame, text=f"Location: {entry.get('city', 'N/A')}, {entry.get('state', 'N/A')}", font=("Arial", 12))
            location_label.grid(row=2, column=1, padx=10, pady=5, sticky="w")

            license_label = ctk.CTkLabel(entry_frame, text=f"License: {entry.get('license_number', 'N/A')}", font=("Arial", 12))
            license_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")

            status_label = ctk.CTkLabel(entry_frame, text=f"Type: {entry.get('business_type', 'N/A')}", font=("Arial", 12))
            status_label.grid(row=1, column=1, padx=10, pady=5, sticky="w")

            phone_label = ctk.CTkLabel(entry_frame, text=f"Phone: {entry.get('phone_number', 'N/A')}", font=("Arial", 12))
            phone_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")

            expiration_date_label = ctk.CTkLabel(entry_frame, text=f"Expiration Date: {entry.get('expiration_date', 'N/A')}", font=("Arial", 12))
            expiration_date_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")
            
            # Add the clickable "link" button for current_url
            current_url = entry.get('current_url', None)
            if current_url:
                link_button = ctk.CTkButton(
                    entry_frame, text="Link", width=60,
                    command=lambda url=current_url: webbrowser.open(url)
                )
                link_button.grid(row=3, column=1, padx=10, pady=5, sticky="w")

            self.display_data.append(entry)
        
        self.current_batch += 1

    def on_scroll(self, event=None):
        scroll_direction = -1 if event.delta > 0 else 1
        scroll_position = self.scrollbar.get()[1]
        if scroll_position >= SCROLL_THRESHOLD and scroll_direction > 0:
            if self.current_batch * BATCH_SIZE < len(self.filtered_data):
                self.load_data(append=True)

    def search(self):
        search_term = self.search_var.get().lower()
        matching_entries = [
            entry for entry in self.crawl_data
            if entry.get("owner_name") and search_term in entry["owner_name"].lower()
        ]
        self.filtered_data = matching_entries
        self.current_batch = 0
        self.load_data()

    def cleanup(self):
        print("Stopping crawling process...")
        self.shutdown_event.set()
        self.quit()
        self.destroy()

def signal_handler(sig, frame):
    print("Ctrl-C detected. Exiting gracefully...")
    app.cleanup()
    sys.exit(0)

if __name__ == "__main__":
    shutdown_event = threading.Event()

    # Register the signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)

    # Create and start the application
    app = App(shutdown_event)
    app.protocol("WM_DELETE_WINDOW", app.cleanup)
    app.mainloop()
