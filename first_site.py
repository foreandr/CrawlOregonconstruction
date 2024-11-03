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
import hyperSel.soup_utilities
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup
import sys
import json

driver = None

def extract_total(string):
    match = re.search(r'\((\d+)\s+total\)', string)
    if match:
        return int(match.group(1))
    return 100  # Default to 100 if no match is found

def get_data_from_single_entry(div):
    data = {}
    try:
        rows = div.find_all("tr")
        
        try:
            if business_name := rows[0].find("td", colspan="2"):
                data['owner_name'] = business_name.get_text(strip=True)
            else:
                data['owner_name'] = "N/A"
        except Exception as e:
            print(f"Error extracting owner_name: {e}")
            data['owner_name'] = "N/A"
        
        data['license_number'] = extract_text_with_label(rows[1], 'license_number:')
        
        try:
            data['License Holder'] = rows[1].find("td", colspan="2").get_text(strip=True) if rows[1].find("td", colspan="2") else "N/A"
        except Exception as e:
            print(f"Error extracting License Holder: {e}")
            data['License Holder'] = "N/A"
        
        data['address1'] = try_extract_text(rows[2], default="N/A")
        data['city'] = try_extract_text(rows[3], "td", "N/A")
        data['License Type'] = extract_text_with_label(rows[2], 'Type:')
        data['business_type'] = extract_text_with_label(rows[3], 'Status:')
        data['phone_number'] = try_extract_text(rows[4], "td", "N/A")
        
        issue_date, exp_date = extract_dates(rows[4])
        data['original Issue Date'] = issue_date
        data['expiration_date'] = exp_date
        
        data['County'] = extract_text_with_label(rows[5], 'County:')
        
        try:
            if ccb_tag := rows[5].find("a"):
                data['CCB No'] = ccb_tag.get_text(strip=True)
                data['current_url'] = ccb_tag['href']
            else:
                data['CCB No'], data['current_url'] = "N/A", "N/A"
        except Exception as e:
            print(f"Error extracting CCB No: {e}")
            data['CCB No'], data['current_url'] = "N/A", "N/A"
        
        try:
            signing_info = rows[-1].find("td", colspan="3").get_text(strip=True)
            data['Signing Person Information'] = [line for line in signing_info.splitlines() if line] if signing_info else []
        except Exception as e:
            data['Signing Person Information'] = []

        data['CE Requirements'] = extract_ce_requirements(div)

    except Exception as e:
        pass

    return data

def extract_ce_requirements(div):
    ce_data = {}
    try:
        ce_table = div.find("table", {"border": "0", "cellpadding": "2", "cellspacing": "0"})
        if ce_table:
            rows = ce_table.find_all("tr")

            try:
                ce_data["Total CE Required"] = rows[0].find("b").get_text(strip=True) if rows[0].find("b") else "N/A"
            except Exception as e:
                ce_data["Total CE Required"] = "N/A"

            try:
                requirement_row = rows[1] if len(rows) > 1 else None
                if requirement_row:
                    b_elements = requirement_row.find_all("b")
                    td_elements = requirement_row.find_all("td")
                    
                    ce_data["Required Breakdown"] = {
                        "CC": b_elements[0].get_text(strip=True) if len(b_elements) > 0 else "N/A",
                        "ORL": b_elements[1].get_text(strip=True) if len(b_elements) > 1 else "N/A",
                        "CC Description": td_elements[3].get_text(strip=True) if len(td_elements) > 3 else "N/A"
                    }
                else:
                    ce_data["Required Breakdown"] = {"CC": "N/A", "ORL": "N/A", "Description": "N/A"}
            except Exception as e:
                ce_data["Required Breakdown"] = {"CC": "N/A", "ORL": "N/A", "Description": "N/A"}

            try:
                ce_data["Current CE"] = {
                    "CC": rows[3].find_all("td")[1].get_text(strip=True) if len(rows) > 3 and len(rows[3].find_all("td")) > 1 else "N/A",
                    "CR": rows[4].find_all("td")[1].get_text(strip=True) if len(rows) > 4 and len(rows[4].find_all("td")) > 1 else "N/A",
                    "ORL": rows[5].find_all("td")[1].get_text(strip=True) if len(rows) > 5 and len(rows[5].find_all("td")) > 1 else "N/A"
                }
            except Exception as e:
                ce_data["Current CE"] = {"CC": "N/A", "CR": "N/A", "ORL": "N/A"}

            try:
                last_row = rows[-1]
                if last_row and len(last_row.find_all("td")) > 1:
                    ce_data["Total Held CE"] = last_row.find_all("td")[1].get_text(strip=True)
                else:
                    ce_data["Total Held CE"] = "N/A"
            except Exception as e:
                ce_data["Total Held CE"] = "N/A"

    except Exception as e:
        ce_data = {"Total CE Required": "N/A", "Required Breakdown": {}, "Current CE": {}, "Total Held CE": "N/A"}

    return ce_data

def get_data_from_page(driver):
    soup = hyperSel.selenium_utilities.get_driver_soup(driver)
    entries = []
    for entry in soup.find_all("div", class_="stripe1"):
        try:
            data = get_data_from_single_entry(entry)
            entries.append(data)
        except Exception as e:
            continue

    for entry in soup.find_all("div", class_="stripe0"):
        try:
            data = get_data_from_single_entry(entry)
            entries.append(data)
        except Exception as e:
            continue

    return entries

def extract_text_with_label(row, label):
    try:
        if cell := row.find("td", string=re.compile(label)):
            return cell.next_sibling.get_text(strip=True) if cell.next_sibling else "N/A"
    except Exception as e:
        print(f"Error extracting label {label}: {e}")
    return "N/A"

def extract_dates(row):
    try:
        dates = re.findall(r'\d{2}/\d{2}/\d{4}', row.get_text())
        return (dates[0] if len(dates) > 0 else "N/A", dates[1] if len(dates) > 1 else "N/A")
    except Exception as e:
        print(f"Error extracting dates: {e}")
    return "N/A", "N/A"

def try_extract_text(row, tag="td", default="N/A"):
    try:
        return row.find(tag).get_text(strip=True) if row.find(tag) else default
    except Exception as e:
        print(f"Error extracting text from {tag}: {e}")
    return default

def replace_i_param(url, n):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    query_params['i'] = [str(n)]
    new_query = urlencode(query_params, doseq=True)
    new_url = urlunparse(parsed_url._replace(query=new_query))
    return new_url

def smooth_mouse_move(driver, duration=5):
    start_time = time.time()
    action = ActionChains(driver)
    
    while time.time() - start_time < duration:
        x_offset = random.randint(-10, 10)
        y_offset = random.randint(-10, 10)
        action.move_by_offset(x_offset, y_offset).perform()
        time.sleep(random.uniform(0.05, 0.15))
        action = ActionChains(driver)

def grab_data(driver):
    soup = hyperSel.selenium_utilities.get_driver_soup(driver)
    tag_with_next_item = soup.find("tr", class_="light bodytext")
    next_link = tag_with_next_item.find("a", text="Next 25")
    items_per_page = 100
    next_url = next_link.get("href") + f'&items_per_page={items_per_page}'
    full_url = f"https://www4.cbs.state.or.us/exs/all/mylicsearch/{next_url}"
    all_data = []
    iter_ = 1
    total = extract_total(str(soup))
    
    while iter_ < total:
        hyperSel.selenium_utilities.go_to_site(driver, full_url)
        time.sleep(20)
        loop_data = get_data_from_page(driver)
        for data in loop_data:
            all_data.append(data)
        iter_ += items_per_page
        full_url = replace_i_param(full_url, iter_)
        time.sleep(random.uniform(3, 10))

    flat_json = convert_big_json_to_flat_json(big_json=all_data)
    hyperSel.log_utilities.log_data(flat_json)

def run(queue):
    global driver
    url = "https://www4.cbs.state.or.us/exs/all/mylicsearch/index.cfm?fuseaction=search.show_search_name&group_id=30"
    driver = hyperSel.selenium_utilities.open_site_selenium(url)
    hyperSel.selenium_utilities.maximize_the_window(driver)

    print("Page loaded. Waiting for Submit to be clicked.")
    while True:
        if not queue.empty():
            message = queue.get()
            if message == "submit_clicked":
                input_button_element_xpath = '''//*[@id="main"]/div/div/div/div/div[3]/div/form/div/div/div[6]/input[1]'''
                element = hyperSel.selenium_utilities.select_element_by_xpath(driver, input_button_element_xpath)
                element.click()

                try:
                    grab_data(driver)
                except Exception as e:
                    pass
                
                queue.put("shutdown")  
                break

def gui(queue):
    def on_submit():
        queue.put("submit_clicked")
        print("clicked button")

    def check_for_shutdown():
        global driver
        if not queue.empty():
            message = queue.get()
            if message == "shutdown":
                print("Shutting down tkinter window.")
                try:
                    hyperSel.selenium_utilities.close_driver(driver)
                except Exception as e:
                    pass
                root.destroy()
        root.after(500, check_for_shutdown)

    root = tk.Tk()
    root.title("Simple GUI")
    root.geometry("300x150")

    check_var1 = tk.BooleanVar()
    check_var2 = tk.BooleanVar()

    checkbox1 = tk.Checkbutton(root, text="I HAVE CLICKED 'I'm not a robot'", variable=check_var1)
    checkbox1.pack(pady=5)

    checkbox2 = tk.Checkbutton(root, text="I HAVE ENTERED MY SEARCH TERMS", variable=check_var2)
    checkbox2.pack(pady=5)

    submit_button = tk.Button(root, text="Submit", bg="green", command=on_submit)
    submit_button.pack(pady=10)

    check_for_shutdown()
    root.mainloop()

def convert_big_json_to_flat_json(big_json, parent_key='', sep='_'):
        """
        Recursively flattens a nested JSON dictionary into a flat dictionary.

        Args:
            big_json (dict): The nested JSON dictionary to flatten.
            parent_key (str, optional): The base key string for recursion. Defaults to ''.
            sep (str, optional): The separator between keys. Defaults to '_'.

        Returns:
            dict: A flat dictionary with no nested sub-objects.
        """
        flat_json = {}
        for key, value in big_json.items():
            # Construct the new key by appending the current key to the parent key
            new_key = f"{parent_key}{sep}{key}" if parent_key else key

            if isinstance(value, dict):
                # Recursively flatten the sub-dictionary
                flat_json.update(convert_big_json_to_flat_json(value, new_key, sep=sep))
            elif isinstance(value, list):
                # Convert lists to a semicolon-separated string or "N/A" if empty
                if all(isinstance(item, (str, int, float)) for item in value):
                    # If all items are primitive types, join them
                    flat_json[new_key] = "; ".join(map(str, value)) if value else "N/A"
                else:
                    # If items are complex (e.g., dicts), represent them as JSON strings
                    flat_json[new_key] = "; ".join([str(item) for item in value]) if value else "N/A"
            else:
                # Assign the value directly, replacing empty strings or None with "N/A"
                flat_json[new_key] = value if value not in [None, ""] else "N/A"

        return flat_json

def main():
    communication_queue = queue.Queue()
    gui_thread = threading.Thread(target=gui, args=(communication_queue,))
    gui_thread.start()
    run(communication_queue)

if __name__ == "__main__":
    main()
