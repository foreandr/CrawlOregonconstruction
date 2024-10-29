import customtkinter as ctk
import json
from datetime import datetime
import time
import threading
import signal
import sys

# Load data from JSON file function
def load_crawl_data(filepath="./logs/crawl_data.json"):
    """
    Load crawl data from a JSON file and return it as a list of dictionaries.
    """
    with open(filepath, "r") as file:
        data = json.load(file)
    return data

# Initialize the main application window
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("License Data Viewer")
        self.geometry("1400x500")  # Increase width to accommodate the HUD panel and progress bar

        # Stop flag for controlled exit
        self.stop_flag = threading.Event()
        
        # Left side layout
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(self, textvariable=self.search_var, width=600, placeholder_text="Search by name")
        self.search_entry.grid(row=0, column=0, padx=20, pady=20, columnspan=2)
        
        self.search_button = ctk.CTkButton(self, text="Search", command=self.search, width=100)
        self.search_button.grid(row=0, column=2, padx=10, pady=20)
        
        # Data display frame (Left side)
        self.data_frame = ctk.CTkScrollableFrame(self, width=700, height=400)
        self.data_frame.grid(row=1, column=0, columnspan=3, padx=20, pady=10, sticky="nsew")
        
        # Right side HUD panel
        self.hud_frame = ctk.CTkFrame(self, width=280, height=400)
        self.hud_frame.grid(row=1, column=3, padx=20, pady=10, sticky="ns")
        
        # Load initial data from JSON file
        self.crawl_data = load_crawl_data()
        self.filtered_data = self.filter_expiration(self.crawl_data)  # Default filter to remove items with no expiration
        self.load_data(self.filtered_data)
        
        # HUD contents
        self.total_data_label = ctk.CTkLabel(self.hud_frame, text=f"TOTAL DATA: {len(self.filtered_data)}", font=("Arial", 14, "bold"))
        self.total_data_label.pack(pady=(20, 10))

        self.expiration_filter_var = ctk.BooleanVar(value=True)
        self.expiration_filter_checkbox = ctk.CTkCheckBox(
            self.hud_frame, 
            text="Has Expiration Date", 
            variable=self.expiration_filter_var, 
            command=self.apply_filters
        )
        self.expiration_filter_checkbox.pack(pady=(10, 20))
        
        # Sorting Buttons
        self.sort_asc_button = ctk.CTkButton(self.hud_frame, text="Sort by Expiration (Newest First)", command=lambda: self.sort_by_expiration(reverse=True))
        self.sort_asc_button.pack(pady=(5, 10))

        self.sort_desc_button = ctk.CTkButton(self.hud_frame, text="Sort by Expiration (Oldest First)", command=lambda: self.sort_by_expiration(reverse=False))
        self.sort_desc_button.pack(pady=(5, 10))

        # Progress bar setup
        self.progress_frame = ctk.CTkFrame(self, width=280, height=400)
        self.progress_frame.grid(row=1, column=4, padx=20, pady=10, sticky="ns")

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, width=250)
        self.progress_bar.grid(row=0, column=0, padx=20, pady=(30, 10))
        
        self.progress_label = ctk.CTkLabel(self.progress_frame, text="Crawling...", font=("Arial", 12, "bold"))
        self.progress_label.grid(row=1, column=0, pady=(10, 0))
        
        self.time_label = ctk.CTkLabel(self.progress_frame, text="Time elapsed: 0s", font=("Arial", 12))
        self.time_label.grid(row=2, column=0, pady=(10, 20))
        
        # Start the crawl simulation in a separate daemon thread
        self.crawl_thread = threading.Thread(target=self.simulate_crawl, daemon=True)
        self.crawl_thread.start()

    def load_data(self, data):
        """Clear the data frame and load the data entries with alternating colors."""
        for widget in self.data_frame.winfo_children():
            widget.destroy()
        
        colors = ["#2E2E2E", "#393939"]
        
        for index, entry in enumerate(data):
            entry_frame = ctk.CTkFrame(self.data_frame, corner_radius=10, fg_color=colors[index % 2])
            entry_frame.pack(fill="x", padx=5, pady=5)
            
            # Name and location row
            name_label = ctk.CTkLabel(entry_frame, text=f"Name: {entry.get('owner_name', 'N/A')}", font=("Arial", 14, "bold"))
            name_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

            location_label = ctk.CTkLabel(entry_frame, text=f"Location: {entry.get('city', 'N/A')}, {entry.get('state', 'N/A')}", font=("Arial", 12))
            location_label.grid(row=0, column=1, padx=10, pady=5, sticky="w")

            # License and status row
            license_label = ctk.CTkLabel(entry_frame, text=f"License: {entry.get('license_number', 'N/A')}", font=("Arial", 12))
            license_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")

            status_label = ctk.CTkLabel(entry_frame, text=f"Status: {entry.get('business_type', 'N/A')}", font=("Arial", 12))
            status_label.grid(row=1, column=1, padx=10, pady=5, sticky="w")

            # Phone and address row (symmetric with zip included)
            phone_label = ctk.CTkLabel(entry_frame, text=f"Phone: {entry.get('phone_number', 'N/A')}", font=("Arial", 12))
            phone_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")

            address = f"{entry.get('address1', 'N/A')}, {entry.get('unit', '')}, {entry.get('city', 'N/A')}, {entry.get('state', 'N/A')} {entry.get('zip', 'N/A')}"
            address_label = ctk.CTkLabel(entry_frame, text=f"Address: {address}", font=("Arial", 12))
            address_label.grid(row=2, column=1, padx=10, pady=5, sticky="w")

            # Effective and expiration dates row
            effective_date_label = ctk.CTkLabel(entry_frame, text=f"Effective Date: {entry.get('effective_date', 'N/A')}", font=("Arial", 12))
            effective_date_label.grid(row=3, column=0, padx=10, pady=5, sticky="w")

            expiration_date_label = ctk.CTkLabel(entry_frame, text=f"Expiration Date: {entry.get('expiration_date', 'N/A')}", font=("Arial", 12))
            expiration_date_label.grid(row=3, column=1, padx=10, pady=5, sticky="w")

            # Crawl time row
            crawl_time_label = ctk.CTkLabel(entry_frame, text=f"Most Recent Crawl Time: {entry.get('recent_scrape_time', 'N/A')}", font=("Arial", 12, "italic"))
            crawl_time_label.grid(row=4, column=0, columnspan=2, padx=10, pady=5, sticky="w")

    def simulate_crawl(self):
        """Simulates a crawl process by updating the progress bar."""
        start_time = time.time()
        for i in range(1, 101):
            if self.stop_flag.is_set():
                return  # Exit if stop flag is set

            # Update progress bar
            self.progress_bar.set(i / 100)
            time_elapsed = int(time.time() - start_time)
            
            # Update progress label and time elapsed
            self.time_label.configure(text=f"Time elapsed: {time_elapsed}s")
            self.progress_label.configure(text="Crawling..." if i < 100 else "Done Crawling")
            
            if i == 100:
                # Set the progress bar color to green when done
                self.progress_bar.configure(fg_color="green")
                
            # Update the GUI and delay to simulate crawl time
            self.update()
            time.sleep(0.1)  # Simulate work being done

    def search(self):
        """Filter data based on search input and apply expiration filter."""
        search_term = self.search_var.get().lower()
        matching_entries = [entry for entry in self.crawl_data if search_term in entry.get("owner_name", "").lower()]
        self.filtered_data = matching_entries
        self.apply_filters()

    def apply_filters(self):
        """Apply expiration date filter and update the displayed data."""
        if self.expiration_filter_var.get():
            self.filtered_data = self.filter_expiration(self.filtered_data)
        else:
            self.filtered_data = self.crawl_data
        self.load_data(self.filtered_data)
        self.total_data_label.configure(text=f"TOTAL DATA: {len(self.filtered_data)}")

    def filter_expiration(self, data):
        """Return only entries with an expiration date."""
        return [entry for entry in data if entry.get("expiration_date")]

    def sort_by_expiration(self, reverse):
        """Sort data by expiration date, handling missing dates gracefully."""
        try:
            self.filtered_data.sort(
                key=lambda x: datetime.strptime(x["expiration_date"], "%m/%d/%Y") if x.get("expiration_date") else datetime.min,
                reverse=reverse
            )
            self.load_data(self.filtered_data)
        except Exception as e:
            print(f"Sorting error: {e}")

    def cleanup(self):
        """Perform cleanup operations on exit."""
        print("Stopping crawling process...")
        self.stop_flag.set()
        self.quit()
        self.destroy()

# Signal handler for graceful shutdown on Ctrl-C
def signal_handler(signal, frame):
    print("\nCtrl-C detected. Exiting gracefully...")
    app.cleanup()
    sys.exit(0)

# Register the signal handler
signal.signal(signal.SIGINT, signal_handler)

# Run the app
if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.cleanup)  # Handle window close events
    app.mainloop()
