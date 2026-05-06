# Automated News Extraction System Using Web Scraping

A Flask web application that collects business and company news from multiple RSS feeds, filters articles by selected companies, extracts readable article content, and generates concise summaries.

## Features

- Fetches news from global business, technology, and company RSS feeds
- Filters articles by company name
- Removes duplicate articles by link
- Extracts main article text from news pages
- Generates article summaries using TextRank
- Provides a simple web interface for browsing news and summaries

## Tech Stack

- Python
- Flask
- Requests
- Feedparser
- BeautifulSoup
- Readability
- Sumy

## Project Structure

```text
.
├── app.py
├── static/
│   └── style.css
└── templates/
    ├── article.html
    ├── index.html
    └── summary.html
```

## Installation

1. Clone the repository:

```bash
git clone https://github.com/charan0704-sai/Automated-News-Extraction-System-Using-Web-Scraping.git
cd Automated-News-Extraction-System-Using-Web-Scraping
```

2. Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install flask requests feedparser beautifulsoup4 readability-lxml sumy nltk
```

4. Run the application:

```bash
python app.py
```

5. Open the app in your browser:

```text
http://127.0.0.1:5000
```

## Usage

Select a company from the web interface to view related news articles. Open an article summary to extract the main content and generate a concise summary.

## Description

This project is designed to make company news tracking easier by collecting information from many online sources in one place. It uses RSS feeds for article discovery, web scraping for content extraction, and natural language processing for summarization.
