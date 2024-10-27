import tkinter as tk
import threading
import queue
import hyperSel
import hyperSel.log_utilities
import hyperSel.nodriver_utilities
import re
import hyperSel.selenium_utilities
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import time
import random
from selenium.webdriver.common.action_chains import ActionChains
def extract_total(string):
    match = re.search(r'\((\d+)\s+total\)', string)
    if match:
        return int(match.group(1))
    return 100  # Default to 100 if no match is found

def get_data_from_single_entry(div):
    data = {}
    try:
        # Get all table rows
        rows = div.find_all("tr")
        
        # Extract Business Name
        try:
            if business_name := rows[0].find("td", colspan="2"):
                data['Business Name'] = business_name.get_text(strip=True)
            else:
                data['Business Name'] = "N/A"
        except Exception as e:
            print(f"Error extracting Business Name: {e}")
            data['Business Name'] = "N/A"
        
        # Extract License/Registration No
        data['License/Registration No'] = extract_text_with_label(rows[1], 'License/Registration No:')
        
        # Extract License Holder Name
        try:
            data['License Holder'] = rows[1].find("td", colspan="2").get_text(strip=True) if rows[1].find("td", colspan="2") else "N/A"
        except Exception as e:
            print(f"Error extracting License Holder: {e}")
            data['License Holder'] = "N/A"
        
        # Extract Address
        data['Address'] = try_extract_text(rows[2], default="N/A")
        
        # Extract City/State/ZIP
        data['City/State/ZIP'] = try_extract_text(rows[3], "td", "N/A")
        
        # Extract License Type
        data['License Type'] = extract_text_with_label(rows[2], 'Type:')
        
        # Extract License Status
        data['Status'] = extract_text_with_label(rows[3], 'Status:')
        
        # Extract Phone Number
        data['Phone'] = try_extract_text(rows[4], "td", "N/A")
        
        # Extract Issue and Expiration Dates
        issue_date, exp_date = extract_dates(rows[4])
        data['Original Issue Date'] = issue_date
        data['Expiration Date'] = exp_date
        
        # Extract County
        data['County'] = extract_text_with_label(rows[5], 'County:')
        
        # Extract CCB No and link, if available
        try:
            if ccb_tag := rows[5].find("a"):
                data['CCB No'] = ccb_tag.get_text(strip=True)
                data['CCB Link'] = ccb_tag['href']
            else:
                data['CCB No'], data['CCB Link'] = "N/A", "N/A"
        except Exception as e:
            print(f"Error extracting CCB No: {e}")
            data['CCB No'], data['CCB Link'] = "N/A", "N/A"
        
        # Extract Signing Person Information
        try:
            signing_info = rows[-1].find("td", colspan="3").get_text(strip=True)
            data['Signing Person Information'] = [line for line in signing_info.splitlines() if line] if signing_info else []
        except Exception as e:
            # print(f"Error extracting Signing Person Information: {e}")
            data['Signing Person Information'] = []

    except Exception as e:
        # print(f"Error parsing div: {e}")
        pass

    return data

def get_data_from_page(driver):
    soup = hyperSel.selenium_utilities.get_driver_soup(driver)
    entries = []
    for entry in soup.find_all("div", class_="stripe1"):
        try:
            data = get_data_from_single_entry(entry)
            entries.append(data)
        except Exception as e:
            # print(e)
            continue
    return entries

def extract_text_with_label(row, label):
    # Find specific text after the label within a table cell
    try:
        if cell := row.find("td", string=re.compile(label)):
            return cell.next_sibling.get_text(strip=True) if cell.next_sibling else "N/A"
    except Exception as e:
        print(f"Error extracting label {label}: {e}")
    return "N/A"

def extract_dates(row):
    # Find dates within text
    try:
        dates = re.findall(r'\d{2}/\d{2}/\d{4}', row.get_text())
        return (dates[0] if len(dates) > 0 else "N/A", dates[1] if len(dates) > 1 else "N/A")
    except Exception as e:
        print(f"Error extracting dates: {e}")
    return "N/A", "N/A"

def try_extract_text(row, tag="td", default="N/A"):
    # Try-except wrapper to extract text safely
    try:
        return row.find(tag).get_text(strip=True) if row.find(tag) else default
    except Exception as e:
        print(f"Error extracting text from {tag}: {e}")
    return default

def replace_i_param(url, n):
    # Parse the URL
    parsed_url = urlparse(url)
    
    # Parse query parameters
    query_params = parse_qs(parsed_url.query)
    
    # Update the 'i' parameter
    query_params['i'] = [str(n)]
    
    # Rebuild the query string
    new_query = urlencode(query_params, doseq=True)
    
    # Rebuild the URL with the new query
    new_url = urlunparse(parsed_url._replace(query=new_query))
    
    return new_url

def smooth_mouse_move(driver, duration=5):
    start_time = time.time()
    action = ActionChains(driver)
    
    while time.time() - start_time < duration:
        # Generate small, random movements
        x_offset = random.randint(-10, 10)  # small random x offset
        y_offset = random.randint(-10, 10)  # small random y offset

        # Move mouse by small offset
        action.move_by_offset(x_offset, y_offset).perform()
        
        # Wait a little between movements to make it smooth
        time.sleep(random.uniform(0.05, 0.15))

        # Reset the action chain to avoid stacking
        action = ActionChains(driver)

def grab_data(driver):
    soup = hyperSel.selenium_utilities.get_driver_soup(driver)
    tag_with_next_item  = soup.find("tr", class_="light bodytext")
    next_link = tag_with_next_item.find("a", text="Next 25")
    items_per_page = 100 # 25 50
    next_url = next_link.get("href") + f'&items_per_page={items_per_page}'
    full_url = f"https://www4.cbs.state.or.us/exs/all/mylicsearch/{next_url}"
    # https://www4.cbs.state.or.us/exs/all/mylicsearch/index.cfm?i=101&fuseaction=search%2Eget%5Fname%5Fresults&search_input=a&group_id=30&prev_fa=search%2Eshow%5Fsearch%5Fname&search_type=bus%5Fname&search_include_inactive=0&items_per_page=100
    # https://www4.cbs.state.or.us/exs/all/mylicsearch/index.cfm?i=261&fuseaction=search%2Eget%5Fname%5Fresults&search_input=a&group_id=30&prev_fa=search%2Eshow%5Fsearch%5Fname&search_type=bus%5Fname&search_include_inactive=0
    all_data = []
    iter_= 1
    total = extract_total(string=str(soup))
    
    while iter_ < total:
        
        hyperSel.selenium_utilities.go_to_site(driver, full_url)
        print("CLICK LINK, WAIT 20 SECONDS")
        time.sleep(20)

        loop_data = get_data_from_page(driver)
        for data in loop_data:
            all_data.append(data)

        print(iter_, len(loop_data))

        iter_+=items_per_page
        full_url = replace_i_param(full_url, iter_)
        time.sleep(random.uniform(3, 10))
        # smooth_mouse_move(driver, duration=5)
        #print(iter_)
        print(full_url)

    print("ALL DATA:" , len(all_data))
    hyperSel.log_utilities.log_data(all_data)


# Main function that pauses after loading the page
def main(queue):
    url = "https://www4.cbs.state.or.us/exs/all/mylicsearch/index.cfm?fuseaction=search.show_search_name&group_id=30"
    driver = hyperSel.selenium_utilities.open_site_selenium(url)
    hyperSel.selenium_utilities.maximize_the_window(driver)

    print("Page loaded. Waiting for Submit to be clicked.")
    while True:
        if not queue.empty():
            message = queue.get()
            if message == "submit_clicked":
                print("Proceeding with next step after Submit click")
                input_button_element_xpath = '''//*[@id="main"]/div/div/div/div/div[3]/div/form/div/div/div[6]/input[1]'''
                element = hyperSel.selenium_utilities.select_element_by_xpath(driver, input_button_element_xpath)
                element.click()

                grab_data(driver)  # Call hello_world() and exit program
                break  # This line is technically redundant due to sys.exit()

# GUI function
def gui(queue):
    def on_submit():
        queue.put("submit_clicked")  # Signal that Submit button was clicked
        print("clicked button")

    def toggle_submit():
        if check_var1.get() and check_var2.get():
            submit_button.config(state="normal", bg="green")
        else:
            submit_button.config(state="disabled", bg="grey")

    # Initialize main window
    root = tk.Tk()
    root.title("Simple GUI")
    root.geometry("300x150")

    # Checkboxes
    check_var1 = tk.BooleanVar()
    check_var2 = tk.BooleanVar()

    checkbox1 = tk.Checkbutton(root, text="I HAVE CLICKED 'I'm not a robot'", variable=check_var1, command=toggle_submit)
    checkbox1.pack(pady=5)

    checkbox2 = tk.Checkbutton(root, text="I HAVE ENTERED MY SEARCH TERMS", variable=check_var2, command=toggle_submit)
    checkbox2.pack(pady=5)

    # Submit button (initially disabled)
    submit_button = tk.Button(root, text="Submit", state="disabled", bg="grey", command=on_submit)
    submit_button.pack(pady=10)

    # Run the main loop
    root.mainloop()

# Main execution to run GUI and main function in parallel
if __name__ == "__main__":
    # Queue for communication between threads
    communication_queue = queue.Queue()

    # Start GUI in a separate thread
    gui_thread = threading.Thread(target=gui, args=(communication_queue,))
    gui_thread.start()

    # Run main in the main thread
    main(communication_queue)

    # add this CE required
