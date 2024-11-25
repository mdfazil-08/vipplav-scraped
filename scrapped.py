import json
import logging
import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, NoSuchWindowException
from fake_useragent import UserAgent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    # Initialize the WebDriver with fake user-agent
    logging.info("Initializing the WebDriver with fake user-agent.")
    ua = UserAgent()
    options = webdriver.ChromeOptions()
    options.add_argument(f'user-agent={ua.random}')  # Set fake user-agent
    driver = webdriver.Chrome(options=options)  # or webdriver.Firefox()

    # Open the main URL
    url = "https://telugu.oneindia.com/news/india/?ref_source=OI-TE&ref_medium=Carousel-Menu&ref_campaign=Header-Menu"
    logging.info(f"Opening the URL: {url}")
    driver.get(url)
    time.sleep(3)  # Wait for the page to load

    processed_links = set()
    stop_date = "December 31, 2023"

    # Load processed links if the file exists
    if os.path.exists('processed_links.json'):
        with open('processed_links.json', 'r', encoding='utf-8') as f:
            processed_links = set(json.load(f))
        logging.info(f"Loaded {len(processed_links)} processed links from 'processed_links.json'.")

    while True:
        # Extract all href links inside the div with class "oi-article-title"
        logging.info("Extracting article titles and their href links.")
        new_articles_found = False

        titles = driver.find_elements(By.XPATH, '//*[@class="oi-article-title"]/a')
        for title_element in titles:
            title_text = title_element.text
            href_link = title_element.get_attribute('href')

            if href_link in processed_links:
                continue  # Skip already processed links

            new_articles_found = True  # Found at least one new article

            logging.info(f"Title: {title_text}")
            logging.info(f"Link: {href_link}")

            # Open the href link in a new tab
            driver.execute_script("window.open('');")
            driver.switch_to.window(driver.window_handles[-1])
            logging.info(f"Navigating to the article page: {href_link}")
            driver.get(href_link)
            time.sleep(2)  # Wait for the page to load

            # Extract the article content (h1, datetime, and paragraphs inside <p> tags)
            try:
                logging.info("Extracting the article content.")
                title = driver.find_element(By.TAG_NAME, 'h1').text
                datetime_tag = driver.find_element(By.TAG_NAME, 'time')
                datetime = datetime_tag.text.strip()
                
                # Check if the article date is the stop date
                if stop_date in datetime:
                    logging.info(f"Found the stop date: {datetime}. Stopping extraction.")
                    driver.quit()
                    return  # Exit the script if the stop date is found

                # Extract all <p> tags within the article and format content as a list
                paragraphs = driver.find_elements(By.TAG_NAME, 'p')
                content = [p.text.replace('\n', ' ') for p in paragraphs]

                # Extract category (adjust selector as needed)
                try:
                    category = driver.find_element(By.CSS_SELECTOR, 'meta[property="article:section"]').get_attribute('content')
                except NoSuchElementException:
                    category = "Unknown"  # Default if the category is not found
                
                logging.info(f"Content extracted for title: {title}")

                # Save the article data incrementally in the required format
                with open('articles.json', 'a', encoding='utf-8') as f:
                    f.write(json.dumps({
                        "title": title,
                        "href": href_link,
                        "category": category,
                        "content": content
                    }, ensure_ascii=False, indent=2) + '\n')
                logging.info(f"Article data saved for title: {title}")
            except NoSuchElementException:
                logging.info(f"Article content not found for title: {title_text}. Skipping.")
            except NoSuchWindowException:
                logging.warning(f"Window closed unexpectedly while processing title: {title_text}. Skipping.")

            # Save the processed link incrementally
            processed_links.add(href_link)
            with open('processed_links.json', 'w', encoding='utf-8') as f:
                json.dump(list(processed_links), f)
            logging.info(f"Processed link saved: {href_link}")

            # Close the tab and switch back to the main window
            try:
                if len(driver.window_handles) > 1:
                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])
                    logging.info(f"Closed article tab and returned to the main page.")
                    time.sleep(2)  # Add sleep time after returning to the main page
                else:
                    logging.warning("Attempted to close a tab, but no additional tabs were found.")
            except NoSuchWindowException:
                logging.warning("No such window found while trying to switch back to the main page.")

        # Check if we found any new articles in this iteration
        if not new_articles_found:
            logging.info("No new articles found on this page.")

        # Try clicking the 'Load More' button with the class 'btn'
        try:
            logging.info("Attempting to click the 'Load More' button.")
            load_more_button = driver.find_element(By.CSS_SELECTOR, "a[class='oi-city-next'] button[class='btn']")
            driver.execute_script("arguments[0].click();", load_more_button)
            logging.info("'Load More' button clicked. Waiting for content to load.")
            time.sleep(3)  # Wait for new content to load
        except NoSuchElementException:
            logging.info("'Load More' button not found. No more content to load.")
            break  # Exit the loop if 'Load More' button is not found

    # Close the driver
    logging.info("Closing the WebDriver.")
    driver.quit()
    logging.info("Web scraping completed.")

if _name_ == "_main_":
    main()
