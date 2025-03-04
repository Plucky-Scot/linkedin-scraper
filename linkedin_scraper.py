import time
from datetime import datetime
import csv
import sys
import re
import os
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium_stealth import stealth
from langdetect import detect

MAX_RESULTS_PAGES = 5 # number of pages of results to extract from
JOB_TERMS = ["software developer", "programmer"]
LOCATION_TERMS = ["Scotland", "Norway", "Germany"]
FILTER_TERMS = ["junior", "senior", "postdoctoral", "intern", "trainee", "student", "scholarship", "study"]
DATE_FILTER = "Past week" # Values: "Any time", "Past month", "Past week", "Past 24 hours"
CSV_PATH = f"./jobs_{datetime.now().strftime('%y-%m-%d_%H-%M')}.csv"
LANG = "en" # language of jobs

options = Options()
options.add_argument("--memory-model-cache-size-mb=512")
options.add_argument("--enable-javascript")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)
# Change for Windows
# driver = webdriver.Chrome(executable_path=driver_path, options=options)
driver = webdriver.Chrome(options=options)
actions = ActionChains(driver)

stealth(
    driver,
    languages=["en-US", "en"],
    vendor="Google Inc.",
    platform="Linux",
    webgl_vendor="Intel Inc.",
    renderer="Intel Iris Graphics",
    fix_hairline=True,
)


def clean_string(text):
    """
    Clean unwanted characters from strings.

    Args:
        text (str): The text to clean.

    Returns:
        str: The cleaned text.
    """
    text = text.replace('About the company', '')
    text = text.replace('About the job', '')
    text = ' '.join(re.sub(r'[^\x00-\x7F]+', ' ', text).split())
    return text


def extract_job_data(soup):
    """
    Extract the data about a job listing from the html.

    Args:
        soup (Beautiful Soup object): The html source to extract from.

    Returns:
        dict or False: The extracted jobs data or False.
    """
    job_data = {}
    try:
        # Extract title and URL
        title_element = soup.find('h1')
        if not title_element or detect(title_element.text) != LANG:
            return False
        job_data['title'] = title_element.text.strip()
        # filter out unwanted jobs
        for term in FILTER_TERMS:
            if term.lower() in job_data['title'].lower():
                return False
        url_element = title_element.find('a')
        if url_element:
            job_data['url'] = url_element.get('href', '')
        else:
            return False

        # Extract location, date, and applicants from description container
        desc_container = soup.find('div', class_='job-details-jobs-unified-top-card__primary-description-container')
        info = ''
        if desc_container:
            spans = desc_container.find_all('span')
            for span in spans:
                info += span.text.strip()
        parsed_info = parse_job_info(info)
        job_data['location'] = parsed_info['location']
        job_data['date'] = parsed_info['date']
        job_data['applicants'] = parsed_info['applicants']
        # Extract job description
        description_element = soup.find('div', id='job-details')
        job_data['description'] = clean_string(description_element.text.strip()) if description_element else ''
        if detect(job_data['description']) != LANG:
            return False
        # Extract company
        company_element = soup.find('div', class_='jobs-company__box')
        job_data['company'] = clean_string(company_element.text.strip()) if company_element else ''
    except Exception as e:
        print(f"Error extracting job data: {e}")
        return False

    return job_data


def append_job_to_csv(job_data):
    """
    Append the extracted jobs data for a single job to a csv file

    Args:
        job_data (dict): The data to append.

    Returns:
        boolean: True if success, False if exception
    """    
    fieldnames = ['title', 'url', 'location', 'date', 'applicants', 'description', 'company']

    # Check if file exists to determine if we need to write headers
    file_exists = os.path.isfile(CSV_PATH)
    try: 
        with open(CSV_PATH, 'a', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            writer.writerow(job_data)
            return True
    except Exception as e:
        print("Unable to append jobs data to csv\n")
        print(e)
        return False


def parse_job_info(text):
    """
    Parse the location, date posted and applicants part of the job data

    Args:
        text (str): The text to parse.

    Returns:
        dict: The parsed string is returned as a dict.
    """
    if len(text) > 0:
        parts = text.split('·')

        # Extract location (first part)
        location = parts[0].strip()

        # Extract date (second occurrence of time period in middle part)
        date = parts[1].strip().split(' ago')[0] + ' ago'

        # Extract applicants (last part)
        applicants = parts[-1].strip().replace(' applicants', '')

        return {
            "location": location,
            "date": date,
            "applicants": applicants
        }
    return {
        "location": 'Unspecified',
        "date": 'Unspecified',
        "applicants": 'Unspecified'
    }


driver.get("https://www.linkedin.com/jobs/search")
driver.maximize_window()  # Maximize the browser window for better visibility

try:
    job_field = WebDriverWait(driver, 180).until(EC.presence_of_element_located((By.XPATH, "//input[contains(@id, 'jobs-search-box-keyword-id-ember')]")))
except TimeoutException:
    print("Loading took too much time!")
    driver.quit()
    sys.exit()

added_urls = [] # holds the completed listings to eliminate duplicates

for job_term in JOB_TERMS:
    for location_term in LOCATION_TERMS:

        # Fill in search fields
        location_field = driver.find_element(By.XPATH, "//input[contains(@id, 'jobs-search-box-location-id-ember')]")
        location_field.clear()
        location_field.send_keys(location_term)
        location_field.send_keys(Keys.RETURN)
        time.sleep(2)

        job_field.clear()
        job_field.send_keys(job_term)
        job_field.send_keys(Keys.RETURN)
        time.sleep(2)

        try: # Filter by date
            driver.find_element(By.XPATH, "//button[contains(@id, 'searchFilter_timePostedRange')]").click()
            time.sleep(2)
            driver.find_element("xpath", f"//input[@name='date-posted-filter-value']//following::span[text()='{DATE_FILTER}']").click()
            time.sleep(2)
            driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Apply current filter')]").click()
            time.sleep(2)
        except Exception as e:
            print("Unable to click on date filter")

        # Loop through pages of jobs results
        for i in range(1,MAX_RESULTS_PAGES):
            print(f"Page{i}\n")
            # Find all job card links
            job_list_items = driver.find_elements(By.XPATH, "//li[contains(@class, 'ember-view')]")

            # Loop through each link
            for list_item in job_list_items: 
                try:
                    actions.move_to_element(list_item).perform()
                    WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable(list_item)
                    )
                    list_item.click()
                    time.sleep(3)

                    content = driver.find_element(By.XPATH, "//div[contains(@class, 'jobs-details__main-content')]")  
                        
                    soup = BeautifulSoup(content.get_attribute('outerHTML'), "html.parser")
                    job_data = extract_job_data(soup)
                    if job_data is not False and job_data['url'] not in added_urls:
                        print("\nAdding job\n")
                        print(job_data)
                        append_job_to_csv(job_data)
                        added_urls.append(job_data['url'])

                except Exception as e:
                    print(f"Error clicking link: {e}")
                    continue

            # Go to next page of jobs or exit loop if none
            try:
                next_button = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'jobs-search-pagination__button--next')]")))
                actions.move_to_element(next_button).perform()
                next_button.click()
                time.sleep(5)
            except Exception as e:
                print("No next button found")
                break

driver.quit()
