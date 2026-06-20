# Rozetka Parser

High-performance asynchronous parser for product data from Rozetka.ua via internal API. Built on aiohttp with optimization for massive parallel loading.

## ✨ Key Features

* Asynchronous data loading via API
* Parallel processing up to 300 connections
* Batch requests for optimization (60 products/request)
* Automatic pagination of all category pages
* Full data extraction: ID, link, brand, price, old price, reviews, rating, category, seller, description
* HTML description cleanup to plain text
* Text output in UTF-8 with separators

## 🚀 Installation

```bash
git clone https://github.com/fedyaqq34356/rozetkaparser.git
cd rozetkaparser
pip install -r requirements.txt
```

## 📝 Usage

```bash
python main.py
```

Enter category URL when prompted:
```
Enter category URL: https://rozetka.com.ua/ua/notebooks/c80004/
```

Data is saved to `ready.txt` file in the current directory.

## 📊 Output Format

```
ID: 12345678
Link: https://rozetka.com.ua/ua/p12345678/
Brand: Apple
Price: 45999 ₴
Old price: 52999 ₴
Reviews: 234 (rating 4.7)
Category ID: 80004
Category link: https://rozetka.com.ua/ua/notebooks/c80004/
Category name: Ноутбуки
Root category: Ноутбуки и компьютеры
Seller: Rozetka
Description: Full product description without HTML tags...
----------------------------------------------------------------------------------------------------
```

## ⚙️ Technical Specifications

| Parameter | Value |
|----------|----------|
| Python version | 3.8+ |
| Concurrent connections | 300 |
| Per-host limit | 100 |
| Request timeout | 60s |
| Batch size | 60 items |
| Output encoding | UTF-8 |

**Stack:**
- `aiohttp` — asynchronous HTTP client
- `beautifulsoup4` — HTML parser
- `lxml` — XML processor

## 📄 License

GNU General Public License v3.0

---

⭐ **If you find this project useful, consider giving it a star!** Happy parsing! 🚀
