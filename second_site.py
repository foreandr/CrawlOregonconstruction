import hyperSel
import hyperSel.log_utilities
import hyperSel.request_utilities
import hyperSel.selenium_utilities
import hyperSel.soup_utilities
import time
from selenium.webdriver.support.ui import Select
import sys
import hard_json
import csv_converter

def get_total_items(driver):
    soup = hyperSel.selenium_utilities.get_driver_soup(driver)
    return hyperSel.soup_utilities.get_text_by_id(soup, "span", "itemsTotal")

def go_to_page_from_home(driver):
    dropdown = Select(hyperSel.selenium_utilities.select_element_by_id(driver, "selSearchType"))
    dropdown.select_by_visible_text("Name")
    time.sleep(2)
    hyperSel.selenium_utilities.click_button(driver, '''//*[@id="searchButton"]''')

def get_primary_data(soup):
    data = {}
    try:
        owner_name = soup.find("span", id="BusinesOwnersName")
        data["owner_name"] = owner_name.get_text(strip=True) if owner_name else None
    except Exception:
        data["owner_name"] = None

    try:
        first_name = soup.find("span", id="BusinesOwnersFirstName")
        data["owner_first_name"] = first_name.get_text(strip=True) if first_name else None
    except Exception:
        data["owner_first_name"] = None

    try:
        last_name = soup.find("span", id="BusinesOwnersLastName")
        data["owner_last_name"] = last_name.get_text(strip=True) if last_name else None
    except Exception:
        data["owner_last_name"] = None

    try:
        principal_name = soup.find("span", id="principalName")
        data["principal_name"] = principal_name.get_text(strip=True) if principal_name else None
    except Exception:
        data["principal_name"] = None

    try:
        dba_name = soup.find("span", id="BusinessDbaName")
        data["doing_business_as"] = dba_name.get_text(strip=True) if dba_name else None
    except Exception:
        data["doing_business_as"] = None

    try:
        address1 = soup.find("span", id="Address1")
        data["address1"] = address1.get_text(strip=True) if address1 else None
    except Exception:
        data["address1"] = None

    try:
        unit = soup.find("span", class_="data-item")
        data["unit"] = unit.get_text(strip=True) if unit else None
    except Exception:
        data["unit"] = None

    try:
        city = soup.find("span", id="City")
        data["city"] = city.get_text(strip=True) if city else None
    except Exception:
        data["city"] = None

    try:
        state = soup.find("span", id="State")
        data["state"] = state.get_text(strip=True) if state else None
    except Exception:
        data["state"] = None

    try:
        zip_code = soup.find("span", id="Zip")
        data["zip"] = zip_code.get_text(strip=True) if zip_code else None
    except Exception:
        data["zip"] = None

    try:
        phone_number = soup.find("span", id="PhoneNumber")
        data["phone_number"] = phone_number.get_text(strip=True) if phone_number else None
    except Exception:
        data["phone_number"] = None

    try:
        county_name = soup.find("span", id="CountyName")
        data["county_name"] = county_name.get_text(strip=True) if county_name else None
    except Exception:
        data["county_name"] = None

    try:
        ubi_number = soup.find("span", id="UBINumber")
        data["ubi_number"] = ubi_number.get_text(strip=True) if ubi_number else None
    except Exception:
        data["ubi_number"] = None

    try:
        business_type = soup.find("span", id="BusinessType")
        data["business_type"] = business_type.get_text(strip=True) if business_type else None
    except Exception:
        data["business_type"] = None

    return data

def grab_secondary_data(soup):
    data = {}

    try:
        specialty1 = soup.find("span", id="SpecialtyName1")
        data["license_specialty_1"] = specialty1.get_text(strip=True) if specialty1 else None
    except Exception:
        data["license_specialty_1"] = None

    try:
        specialty2 = soup.find("span", id="SpecialtyName2")
        data["license_specialty_2"] = specialty2.get_text(strip=True) if specialty2 and specialty2.get("style") != "display: none;" else None
    except Exception:
        data["license_specialty_2"] = None

    try:
        license_number = soup.find("span", id="LicenseNumber")
        data["license_number"] = license_number.get_text(strip=True) if license_number else None
    except Exception:
        data["license_number"] = None

    try:
        effective_date = soup.find("span", id="EffectiveDate")
        data["effective_date"] = effective_date.get_text(strip=True) if effective_date else None
    except Exception:
        data["effective_date"] = None

    try:
        expiration_date = soup.find("span", id="ExpirationDate")
        data["expiration_date"] = expiration_date.get_text(strip=True) if expiration_date else None
    except Exception:
        data["expiration_date"] = None

    try:
        registration = soup.find("span", id="Registration2")
        data["contractor_registration"] = registration.get_text(strip=True) if registration else None
    except Exception:
        data["contractor_registration"] = None

    try:
        associated_licenses = soup.find("span", id="AssociatedLicensesLink")
        if associated_licenses and associated_licenses.get("style") != "display: none;":
            related_link = associated_licenses.find("a", id="relatedLink")
            data["associated_licenses_link"] = related_link["href"] if related_link else None
        else:
            data["associated_licenses_link"] = None
    except Exception:
        data["associated_licenses_link"] = None

    try:
        fraud_link = soup.find("span", id="FraudLink")
        fraud_url = fraud_link.find("a")["href"] if fraud_link else None
        data["fraud_report_link"] = fraud_url if fraud_url else None
    except Exception:
        data["fraud_report_link"] = None

    try:
        license_renewal = soup.find("span", id="LicenseRenewal")
        data["license_renewal"] = license_renewal.get_text(strip=True) if license_renewal else None
    except Exception:
        data["license_renewal"] = None

    return data

def func(driver):
    for i in range(100):
        # print("IN PAGE ITER:", i)
        time.sleep(2)
        attempts = 0
        while True:
            if attempts >= 100:
                break
            try:
                row_to_click = hyperSel.selenium_utilities.select_multiple_elements_by_class(driver, "itemSingleCol")[i]
                row_to_click.click()
                break
            except Exception as e:
                print("THIS CLICK FAILED", attempts)
                time.sleep(0.5)
                attempts += 1
                continue
            
        time.sleep(3)
        data_soup = hyperSel.selenium_utilities.get_driver_soup(driver)
        data = grab_secondary_data(data_soup.find(id="WholeLicense"))
        data2 = get_primary_data(data_soup.find("div", class_="itemLayout"))
        data["current_url"] = driver.current_url

        combined_data = {**data, **data2}
        try:
            if combined_data['address1'] in hard_json.all_addresses:
                # dupe
                pass
            else:
                hyperSel.log_utilities.log_data(combined_data, verbose=False)
                csv_converter.update_csv_with_json(combined_data)
        except Exception as e:
            print(e)
        driver.back()
        

def main(progress_queue=None):
    driver = hyperSel.selenium_utilities.open_site_selenium("https://secure.lni.wa.gov/verify/", show_browser=False)
    hyperSel.selenium_utilities.maximize_the_window(driver)

    go_to_page_from_home(driver)
    time.sleep(2)
    attempts = 0
    total = None
    
    while True:
        attempts += 1
        if attempts >= 15:
            total = 0
            break
        
        try:
            total = int(get_total_items(driver)) + 100
            break
        except Exception as e:
            time.sleep(2)
            print("STUCK HERE", attempts)
            continue   
    
    results_dropdown = Select(hyperSel.selenium_utilities.select_element_by_id(driver, "resultsLengthSelect"))
    results_dropdown.select_by_visible_text("100 items")

    total_time = time.time()

    iter_ = 1
    items_per_page = 100
    page_no = 0
    loops = 0
    while iter_ < total:
        if progress_queue:
            progress_queue.put(iter_ / total)

        time.sleep(1)
        loops += 1
        if loops >= 5000:
            print("SOMETHING HAS GONE BADLY WRONG")
            break

        page_no += 1
        func(driver)
        
        iter_ += items_per_page
        
        time.sleep(5)
        
        # Move to next page
        element = hyperSel.selenium_utilities.get_element_by_class(driver, class_name="nextButton")
        element.click()

    try:
        hyperSel.selenium_utilities.close_driver(driver)
    except Exception as e:
        pass

    if progress_queue:
        progress_queue.put(1)  # Signal 100% completion

    print("TOTAL TIME TAKEN", time.time() - total_time)
    
if __name__ == "__main__":
    from queue import Queue
    progress_queue = Queue()
    main(progress_queue)