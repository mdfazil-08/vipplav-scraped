import json
import logging
import time
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from fake_useragent import UserAgent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    # Create tt directory if not exists
    os.makedirs('tt', exist_ok=True)
    
    # Initialize the WebDriver with fake user-agent
    logging.info("Initializing the WebDriver with fake user-agent.")
    options = webdriver.ChromeOptions()
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    driver = webdriver.Chrome(options=options)

    # Open the main URL
    url = "https://www.sakshi.com/news/family"
    logging.info(f"Opening the URL: {url}")
    driver.get(url)
    time.sleep(10)

    processed_links = set()
    stop_date = datetime.strptime("December 31, 2023", "%B %d, %Y")

    # Load processed links from tt directory
    processed_path = os.path.join('tt', 'processed_links_sakshi.json')
    if os.path.exists(processed_path):
        with open(processed_path, 'r', encoding='utf-8') as f:
            processed_links = set(json.load(f))
        logging.info(f"Loaded {len(processed_links)} processed links.")

    while True:
        new_articles_found = False
        articles = driver.find_elements(By.XPATH, "//ul[@id='news-view']//li//a")

        for article in articles:
            try:
                href_link = article.get_attribute('href')
                if href_link in processed_links:
                    continue

                title = article.find_element(By.XPATH, './/h2').text
                content = article.find_element(By.XPATH, './/div[1]/div[1]').text
                time_text = article.find_element(By.XPATH, './/time').text

                article_date = datetime.strptime(time_text, "%a, %b %d %Y %I:%M %p")

                if article_date <= stop_date:
                    logging.info(f"Reached stop date {article_date}. Stopping extraction.")
                    driver.quit()
                    return

                # Save to tt/article.json
                article_path = os.path.join('tt', 'article.json')
                with open(article_path, 'a', encoding='utf-8') as f:
                    json.dump({
                        "title": title,
                        "href": href_link,
                        "content": content,
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

        # Save processed links in tt directory
        with open(processed_path, 'w', encoding='utf-8') as f:
            json.dump(list(processed_links), f)

        if not new_articles_found:
            logging.info("No new articles found.")

        try:
            load_more_button = driver.find_element(By.CSS_SELECTOR, "a.oi-city-next button.btn")
            driver.execute_script("arguments[0].click();", load_more_button)
            logging.info("Loading more articles...")
            time.sleep(10)
        except NoSuchElementException:
            logging.info("No more articles available.")
            break

    driver.quit()
    logging.info("Scraping completed. Files saved in 'tt' directory.")

if __name__ == "__main__":
    main()