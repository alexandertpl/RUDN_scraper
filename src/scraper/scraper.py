import requests
from bs4 import BeautifulSoup
import csv
import time
import re

BASE_URL = "https://www.chitai-gorod.ru/catalog/books/povesti-i-rasskazy-dlya-detej-110095"
MAX_PAGES_TO_SCRAPE = 3
OUTPUT_CSV_FILE = "chitai_gorod_books_updated.csv"
REQUEST_DELAY = 2

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7"
}

def clean_price(price_str):
    if not price_str:
        return None
    cleaned_price = price_str.replace('\xa0', '').replace(' ', '') 
    cleaned_price = re.sub(r'[^\d,.]', '', cleaned_price) 
    cleaned_price = cleaned_price.replace(',', '.') 
    try:
        if not cleaned_price: 
            return None
        if '.' in cleaned_price:
            return float(cleaned_price)
        else:
            return int(cleaned_price)
    except ValueError:
        match = re.search(r'\d[\d\s]*', price_str)
        if match:
            num_str = re.sub(r'\s', '', match.group(0))
            try:
                return int(num_str)
            except ValueError:
                return None
        return None


def get_book_data_from_page(page_url):
    books_on_page = []

    response = requests.get(page_url, headers=HEADERS, timeout=15)
    
    soup = BeautifulSoup(response.text, 'html.parser')

    product_cards = soup.find_all('article', class_='product-card')

    if not product_cards:
        return books_on_page

    for card in product_cards:
        title, price, author = None, None, None

        title = card.get('data-chg-product-name')
        if not title:
            title_tag = card.find('a', class_='product-card__title')
            if title_tag:
                title = title_tag.text.strip()

        price_str_attr = card.get('data-chg-product-price')
        if price_str_attr:
            try:
                price = float(price_str_attr)
            except ValueError:
                price = clean_price(price_str_attr)
        
        if price is None:
            price_tag = card.find('span', class_='product-price__price')
            if price_tag:
                price_text = price_tag.text.strip()
                price = clean_price(price_text)
      
        author_tag = card.find('span', class_='product-card__subtitle')
        if author_tag:
            author = author_tag.text.strip()
            if author.lower() == "автор не указан":
                author = None
        
        if not author and title:
            title_link_tag = card.find('a', class_='product-card__title')
            if title_link_tag and title_link_tag.get('title'):
                title_attr_text = title_link_tag.get('title')
                match = re.search(r'\(([^)]+)\)$', title_attr_text)
                if match:
                    potential_author = match.group(1).strip()
                    if len(potential_author) < 50 and not potential_author.isdigit():
                        if not title.startswith(potential_author):
                            author = potential_author


        if title:
            books_on_page.append({
                "Title": title,
                "Price": price if price is not None else "Не указана",
                "Author": author if author else "Не указан"
            })

    return books_on_page

def save_to_csv(data, filename):
    keys = data[0].keys()
    with open(filename, 'w', newline='', encoding='utf-8') as output_file:
        dict_writer = csv.DictWriter(output_file, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(data)

def main():
    all_books_data = []
    print(BASE_URL)

    for page_num in range(1, MAX_PAGES_TO_SCRAPE + 1):
        page_url = f"{BASE_URL}?page={page_num}"
        
        books_from_current_page = get_book_data_from_page(page_url)

        if not books_from_current_page and page_num > 1:
            break 

        all_books_data.extend(books_from_current_page)
        print(f"Собрано {len(books_from_current_page)} книг со страницы {page_num}. Всего собрано: {len(all_books_data)}")

        if page_num < MAX_PAGES_TO_SCRAPE:
            print(f"Пауза...")
            time.sleep(REQUEST_DELAY)

    if all_books_data:
        all_books_data = sorted(all_books_data, key=lambda item: str(item.get("Title")).lower())
        save_to_csv(all_books_data, OUTPUT_CSV_FILE)
    else:
        print("Не удалось собрать никаких данных.")

if __name__ == "__main__":
    main()
