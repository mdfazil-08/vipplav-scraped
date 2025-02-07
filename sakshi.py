import json
import logging
import time
import os
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from fake_useragent import UserAgent
import re

category = "family"

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_random_user_agent():
    """Generate a random User-Agent string"""
    ua = UserAgent()
    return ua.random

def setup_driver():
    """Initialize Selenium WebDriver with a fake user-agent"""
    options = webdriver.ChromeOptions()
    fake_user_agent = get_random_user_agent()
    options.add_argument(f'user-agent={fake_user_agent}')
    options.add_argument('--headless')  # Run in headless mode (optional)
    options.add_argument('--disable-blink-features=AutomationControlled')  # Reduce detection
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--incognito')  # Run in incognito mode
    options.add_argument('--disable-extensions')

    logging.info(f"Using User-Agent: {fake_user_agent}")
    
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(120)  # Set a timeout for page load
    return driver

def main():
    os.makedirs(f"{category}", exist_ok=True)
    driver = setup_driver()

    url = "https://www.sakshi.com/news/"
    logging.info(f"Opening the URL: {url}{category}")
    
    try:
        driver.get(f"{url}{category}")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, "//ul[@id='news-view']//li//a")))
    except TimeoutException:
        logging.error("Page load timed out. Exiting.")
        driver.quit()
        return

    processed_links = set()
    stop_date = datetime.strptime("December 31, 2023","%B %d, %Y")

    processed_path = os.path.join(f'{category}', 'processed_links_sakshi.json')
    if os.path.exists(processed_path):
        with open(processed_path, 'r', encoding='utf-8') as f:
            processed_links = set(json.load(f))
        logging.info(f"Loaded {len(processed_links)} processed links.")

    while True:
        new_articles_found = False
        try:
            articles = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//ul[@id='news-view']//li//a"))
            )
        except TimeoutException:
            logging.warning("No articles found or page took too long to load.")
            break

        for article in articles:
            try:
                href_link = article.get_attribute('href')
                if href_link in processed_links:
                    continue

                title = article.find_element(By.XPATH, './/h2').text
                content = article.find_element(By.XPATH, './/div[1]/div[1]').text
                
                filtered_content = re.sub(
                    r"""[\U0001F600-\U0001F64F] | \#[A-Za-z0-9_]+ | https?://\S+ | www\.\S+ | \@\S+ | 
                    [A-Za-z]+ | [“”‘’\"\'…]+ | [-—_/\\|]+ | \.{2,} | \(\)""",
                    '', content, flags=re.UNICODE | re.VERBOSE
                ).strip()
                filtered_content = re.sub(r'\s+', ' ', filtered_content).strip()


                try:
                    time_element = article.find_element(By.XPATH, './/time')
                    time_text = time_element.text.strip()

                    if not time_text:
                        logging.warning("Skipping article due to missing timestamp.")
                        continue

                    logging.info(f"Extracted time text: {time_text}")

            # Convert date format
                    article_date = datetime.strptime(time_text, "%a, %b %d %Y %I:%M %p")

                    if article_date <= stop_date:
                        logging.info(f"Reached stop date {article_date}. Stopping extraction.")
                        driver.quit()
                        return

                except NoSuchElementException:
                    logging.warning("Time element not found, skipping article.")
                    continue
                
                except ValueError:
                    logging.error(f"Time format mismatch: {time_text}, skipping article.")
                    continue
   
                time_text = article.find_element(By.XPATH, './/time').text
                article_date = datetime.strptime(time_text, "%a, %b %d %Y %I:%M %p")

                if article_date <= stop_date:
                    logging.info(f"Reached stop date {article_date}. Stopping extraction.")
                    driver.quit()
                    return

                article_path = os.path.join(f'{category}', 'article.json')
                with open(article_path, 'a', encoding='utf-8') as f:
                    json.dump({
                        "title": title,
                        "href": href_link,
                        "content": filtered_content,
                        "time": time_text
                    }, f, ensure_ascii=False)
                    f.write('\n')

                processed_links.add(href_link)
                new_articles_found = True
                logging.info(f"Processed: {title}")

            except NoSuchElementException as e:
                logging.warning(f"Element missing: {str(e)}")
            except Exception as e:
                logging.error(f"Error: {str(e)}")

        with open(processed_path, 'w', encoding='utf-8') as f:
            json.dump(list(processed_links), f)

        if not new_articles_found:
            logging.info("No new articles found.")

        try:
            load_more_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Load more')]"))
            )
            driver.execute_script("arguments[0].scrollIntoView();", load_more_button)
            time.sleep(random.uniform(2, 5))  # Random sleep to mimic human behavior
            driver.execute_script("arguments[0].click();", load_more_button)
            logging.info("Loading more articles...")
            time.sleep(random.uniform(5, 10))
        except (NoSuchElementException, TimeoutException):
            logging.info("No more articles available.")
            break

    driver.quit()
    logging.info(f"Scraping completed. Files saved in {category} directory.")

if __name__ == "__main__":
    main()
