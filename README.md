# linkedin-scraper
Downloads jobs from Linkedin

Searches for jobs on Linkedin and downloads them to a .csv file.

Uses Beautiful Soup and Selenium with stealth. Also uses langdetect to detect job language.

Runs a Chrome GUI.

The default browser is Chrome so this should be installed or the code updated.

Specify the job title terms to search in JOB_TERMS list. 
Specify the locations in LOCATION_TERMS list.
Specify any filters in FILTER_TERMS.
Use the DATE_FILTER constant to filter by date.

Ideally we would simply pass all these to the Linkedin search field in one string using operators but this doesn't work very well.

Running the code will open a Chrome window. Enter login details manually. Then the script will run automatically.

It is possible to automate logging in but this generally prompts 2FA. It is easier to log in manually then leave the script to run.

When jobs are downloaded the .csv file can be passed to an LLM to assess the suitability of jobs.
