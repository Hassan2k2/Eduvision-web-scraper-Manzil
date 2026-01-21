"""
EduVision Web Scraper
Scrapes university institution data from eduvision.edu.pk
"""

import requests
from bs4 import BeautifulSoup
import csv
import json
import re
import time
from typing import List, Dict, Optional
from urllib.parse import urljoin


def fetch_page(url: str, retries: int = 3, delay: int = 2) -> Optional[str]:
    """
    Fetch HTML content from a URL with retry logic.
    
    Args:
        url: URL to fetch
        retries: Number of retry attempts
        delay: Delay between retries in seconds
        
    Returns:
        HTML content as string, or None if failed
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            if attempt < retries - 1:
                print(f"Request failed (attempt {attempt + 1}/{retries}): {e}")
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print(f"Failed to fetch {url} after {retries} attempts: {e}")
                return None
    return None


def parse_table(html: str) -> Optional[BeautifulSoup]:
    """
    Parse HTML and locate the institutions table.
    
    Args:
        html: HTML content as string
        
    Returns:
        BeautifulSoup object of the table, or None if not found
    """
    try:
        soup = BeautifulSoup(html, 'lxml')
        # Find the table containing institution data
        # The table should have headers: Institute, City, Degree Duration, Fee, Deadline
        table = soup.find('table')
        
        if table is None:
            print("Warning: No table found in HTML")
            return None
            
        # Verify table has the expected headers
        headers = table.find('thead') or table.find('tr')
        if headers:
            header_text = ' '.join([th.get_text(strip=True) for th in headers.find_all(['th', 'td'])])
            expected_keywords = ['Institute', 'City', 'Fee', 'Deadline']
            if not any(keyword in header_text for keyword in expected_keywords):
                print(f"Warning: Table headers may not match expected format: {header_text}")
        
        return table
    except Exception as e:
        print(f"Error parsing HTML: {e}")
        return None


def clean_institute_name(name: str) -> str:
    """
    Remove numbering prefix from institute names (e.g., "1. " -> "").
    
    Args:
        name: Institute name with possible numbering
        
    Returns:
        Cleaned institute name
    """
    # Remove pattern like "1. ", "2. ", etc. from the beginning
    cleaned = re.sub(r'^\d+\.\s*', '', name.strip())
    return cleaned


def parse_fee(fee_text: str) -> int:
    """
    Convert fee text to integer.
    
    Args:
        fee_text: Fee as string (may contain commas or be "0")
        
    Returns:
        Fee as integer
    """
    try:
        # Remove commas and whitespace, then convert to int
        fee_str = fee_text.replace(',', '').strip()
        return int(fee_str) if fee_str else 0
    except (ValueError, AttributeError):
        return 0


def split_degree_duration(degree_duration: str) -> tuple:
    """
    Split "Degree, Duration" into separate degree and duration.
    
    Args:
        degree_duration: Combined degree and duration string (e.g., "BS , 4 Years")
        
    Returns:
        Tuple of (degree, duration)
    """
    if ',' in degree_duration:
        parts = degree_duration.split(',', 1)
        degree = parts[0].strip()
        duration = parts[1].strip() if len(parts) > 1 else ''
    else:
        # Try to split by common patterns
        match = re.match(r'^(.+?)\s+(\d+\s+Years?)$', degree_duration.strip())
        if match:
            degree = match.group(1).strip()
            duration = match.group(2).strip()
        else:
            degree = degree_duration.strip()
            duration = ''
    
    return degree, duration


def extract_rows(table: BeautifulSoup, subject: str = '') -> List[Dict[str, str]]:
    """
    Extract data from table rows.
    
    Args:
        table: BeautifulSoup table element
        subject: Subject field to add to each record
        
    Returns:
        List of dictionaries containing row data
    """
    rows_data = []
    
    try:
        # Find all table rows, skip header row
        rows = table.find_all('tr')
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            
            # Skip header row (typically has <th> or first row with specific text)
            if len(cells) > 0:
                first_cell_text = cells[0].get_text(strip=True)
                # Skip if this looks like a header row
                if first_cell_text in ['Institute', 'City'] or cells[0].name == 'th':
                    continue
                    
            # Extract data from cells (expecting 5 columns)
            if len(cells) >= 5:
                institute_raw = cells[0].get_text(strip=True)
                city = cells[1].get_text(strip=True)
                degree_duration = cells[2].get_text(strip=True)
                fee_text = cells[3].get_text(strip=True)
                deadline = cells[4].get_text(strip=True)
                
                # Clean and process data
                institute = clean_institute_name(institute_raw)
                degree, duration = split_degree_duration(degree_duration)
                fee = parse_fee(fee_text)
                
                # Only add row if it has valid institute name
                if institute:
                    rows_data.append({
                        'Institute': institute,
                        'City': city,
                        'Degree': degree,
                        'Duration': duration,
                        'Fee': fee,
                        'Deadline': deadline,
                        'Subject': subject
                    })
    except Exception as e:
        print(f"Error extracting rows: {e}")
    
    return rows_data


def extract_total_count_and_subject(html: str) -> tuple:
    """
    Extract total count and subject from the page.
    
    Args:
        html: HTML content as string
        
    Returns:
        Tuple of (total_count, subject)
    """
    try:
        soup = BeautifulSoup(html, 'lxml')
        
        # Find heading with format: "263 Universities and Colleges are offering BS Software Engineering in Pakistan"
        # Try h2 first, then look for the text pattern in any element
        heading = soup.find('h2')
        if not heading:
            # Try finding by text pattern
            heading_text_elem = soup.find(string=re.compile(r'\d+\s+Universities?\s+and\s+Colleges?\s+are\s+offering', re.IGNORECASE))
            if heading_text_elem:
                heading_text = str(heading_text_elem).strip()
            else:
                heading_text = None
        else:
            heading_text = heading.get_text(strip=True)
        
        if heading_text:
            # Extract count using regex
            count_match = re.search(r'(\d+)\s+Universities?\s+and\s+Colleges?', heading_text)
            if count_match:
                total_count = int(count_match.group(1))
            else:
                total_count = None
            
            # Extract subject - pattern: "are offering BS Software Engineering in Pakistan"
            # Try pattern: "are offering [Degree] [Subject] in Pakistan"
            subject_match = re.search(r'are\s+offering\s+(?:BS|MS|PhD|Bachelor|Master|Doctorate)\s+(.+?)\s+in\s+Pakistan', heading_text, re.IGNORECASE)
            if subject_match:
                subject = subject_match.group(1).strip()
            else:
                # Try pattern: "[Degree] [Subject] in Pakistan" (without "are offering")
                subject_match = re.search(r'(?:BS|MS|PhD|Bachelor|Master|Doctorate)\s+(.+?)\s+in\s+Pakistan', heading_text, re.IGNORECASE)
                if subject_match:
                    subject = subject_match.group(1).strip()
                else:
                    # Try alternative: look for text between "offering" and "with field" or "in Pakistan"
                    subject_match = re.search(r'offering\s+.+?\s+(.+?)\s+(?:with\s+field|in\s+Pakistan)', heading_text, re.IGNORECASE)
                    if subject_match:
                        # Extract just the subject part (may include degree, so remove it)
                        potential_subject = subject_match.group(1).strip()
                        # Remove degree prefix if present
                        potential_subject = re.sub(r'^(?:BS|MS|PhD|Bachelor|Master|Doctorate)\s+', '', potential_subject, flags=re.IGNORECASE).strip()
                        subject = potential_subject.replace('-', ' ').title() if potential_subject else None
                    else:
                        subject = None
            
            return total_count, subject
        
        return None, None
    except Exception as e:
        print(f"Error extracting total count and subject: {e}")
        return None, None


def extract_total_pages(html: str) -> Optional[int]:
    """
    Extract total number of pages from pagination.
    
    Args:
        html: HTML content as string
        
    Returns:
        Total number of pages, or None if not found
    """
    try:
        soup = BeautifulSoup(html, 'lxml')
        
        # Method 1: Look for "Page X of Y" pattern in any text (including nested)
        # Using find_all with recursive=True to search all text nodes
        page_text_elements = soup.find_all(string=re.compile(r'Page\s+\d+\s+of\s+\d+', re.IGNORECASE))
        for page_text in page_text_elements:
            text_str = str(page_text).strip()
            match = re.search(r'Page\s+\d+\s+of\s+(\d+)', text_str, re.IGNORECASE)
            if match:
                total = int(match.group(1))
                print(f"Found total pages from 'Page X of Y' text: {total}")
                return total
        
        # Method 2: Search all elements for text containing "Page X of Y"
        for elem in soup.find_all(['div', 'span', 'p', 'li', 'h2', 'h3', 'h4']):
            text = elem.get_text(strip=True)
            if text and re.search(r'Page\s+\d+\s+of\s+\d+', text, re.IGNORECASE):
                match = re.search(r'Page\s+\d+\s+of\s+(\d+)', text, re.IGNORECASE)
                if match:
                    total = int(match.group(1))
                    print(f"Found total pages from element text: {total}")
                    return total
        
        # Method 2b: Search the entire HTML text as fallback
        full_text = soup.get_text()
        if re.search(r'Page\s+\d+\s+of\s+\d+', full_text, re.IGNORECASE):
            match = re.search(r'Page\s+\d+\s+of\s+(\d+)', full_text, re.IGNORECASE)
            if match:
                total = int(match.group(1))
                print(f"Found total pages from full page text: {total}")
                return total
        
        # Method 3: Look for pagination links with href containing page-X
        pagination_links = soup.find_all('a', href=re.compile(r'page-\d+', re.IGNORECASE))
        max_page = 1
        for link in pagination_links:
            href = link.get('href', '')
            page_match = re.search(r'page-(\d+)', href, re.IGNORECASE)
            if page_match:
                page_num = int(page_match.group(1))
                if page_num > max_page:
                    max_page = page_num
        
        # Method 4: Look for JavaScript pagination links (browsePage(X))
        js_links = soup.find_all('a', href=re.compile(r'browsePage\(', re.IGNORECASE))
        for link in js_links:
            href = link.get('href', '')
            # Extract number from browsePage(X)
            page_match = re.search(r'browsePage\((\d+)\)', href, re.IGNORECASE)
            if page_match:
                page_num = int(page_match.group(1))
                if page_num > max_page:
                    max_page = page_num
        
        # Method 5: Look at link text for page numbers
        for link in soup.find_all('a'):
            link_text = link.get_text(strip=True)
            # Check if link text is just a number (likely a page number)
            if link_text.isdigit():
                page_num = int(link_text)
                if page_num > max_page:
                    max_page = page_num
        
        if max_page > 1:
            print(f"Found total pages from pagination links: {max_page}")
            return max_page
        
        print("Warning: Could not find total pages, defaulting to 1")
        return None
    except Exception as e:
        print(f"Error extracting total pages: {e}")
        return None


def scrape_page(url: str, subject: str = '') -> List[Dict[str, str]]:
    """
    Main function to scrape a single page.
    
    Args:
        url: URL to scrape
        subject: Subject field to add to each record
        
    Returns:
        List of dictionaries containing scraped data
    """
    print(f"Fetching page: {url}")
    html = fetch_page(url)
    
    if html is None:
        return []
    
    table = parse_table(html)
    if table is None:
        return []
    
    rows_data = extract_rows(table, subject)
    print(f"Extracted {len(rows_data)} rows from page")
    
    return rows_data


def save_to_csv(data: List[Dict[str, str]], filename: str = 'output.csv'):
    """
    Save scraped data to CSV file.
    
    Args:
        data: List of dictionaries containing scraped data
        filename: Output CSV filename
    """
    if not data:
        print("No data to save")
        return
    
    fieldnames = ['Institute', 'City', 'Degree', 'Duration', 'Fee', 'Deadline', 'Subject']
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        print(f"Data saved to {filename}")
    except Exception as e:
        print(f"Error saving to CSV: {e}")


def save_to_json(data: List[Dict[str, str]], filename: str = 'output.json'):
    """
    Save scraped data to JSON file.
    
    Args:
        data: List of dictionaries containing scraped data
        filename: Output JSON filename
    """
    if not data:
        print("No data to save")
        return
    
    try:
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(data, jsonfile, indent=2, ensure_ascii=False)
        print(f"Data saved to {filename}")
    except Exception as e:
        print(f"Error saving to JSON: {e}")


def generate_page_urls(base_url: str, total_pages: int) -> List[str]:
    """
    Generate URLs for all pages.
    
    Args:
        base_url: Base URL (page-1 URL)
        total_pages: Total number of pages
        
    Returns:
        List of URLs for all pages
    """
    urls = []
    # Replace page-1 with page-X for each page
    for page_num in range(1, total_pages + 1):
        url = base_url.replace('-page-1', f'-page-{page_num}')
        urls.append(url)
    return urls


def main():
    """Main entry point."""
    # Base URL (page 1)
    base_url = "https://www.eduvision.edu.pk/institutions-offering-bio-medical-with-field-engineering-at-bachelor-level-in-pakistan-page-1"
    
    print("Fetching first page to get metadata...")
    first_page_html = fetch_page(base_url)
    
    if first_page_html is None:
        print("Failed to fetch first page. Please check the URL and try again.")
        return
    
    # Extract total count and subject from first page
    total_count, subject = extract_total_count_and_subject(first_page_html)
    
    if total_count:
        print(f"Found: {total_count} Universities and Colleges offering {subject or 'the program'}")
    
    # Extract total number of pages
    total_pages = extract_total_pages(first_page_html)
    
    # If we couldn't detect pages but have total count, estimate from count
    if total_pages is None:
        if total_count:
            # Estimate pages: typically ~20 institutions per page
            estimated_pages = (total_count // 20) + (1 if total_count % 20 > 0 else 0)
            print(f"Warning: Could not detect total pages from pagination.")
            print(f"Estimating from total count ({total_count} institutions): ~{estimated_pages} pages")
            total_pages = estimated_pages
        else:
            print("Warning: Could not determine total pages. Scraping only page 1.")
            total_pages = 1
    
    print(f"Total pages to scrape: {total_pages}")
    
    if subject:
        print(f"Subject: {subject}\n")
    else:
        # Fallback: extract from URL pattern: "offering-software-engineering-with-field"
        url_match = re.search(r'offering-([^-]+(?:-[^-]+)*?)-with-field', base_url)
        if url_match:
            subject = url_match.group(1).replace('-', ' ').title()
            print(f"Subject (from URL): {subject}\n")
        else:
            subject = "Bio Medical Engineering"  # Default fallback
            print(f"Subject (default): {subject}\n")
    
    # Generate URLs for all pages
    page_urls = generate_page_urls(base_url, total_pages)
    
    # Scrape all pages
    all_data = []
    for page_num, url in enumerate(page_urls, 1):
        print(f"\n--- Scraping page {page_num}/{total_pages} ---")
        page_data = scrape_page(url, subject or '')
        all_data.extend(page_data)
        
        # Add delay between pages to be respectful
        if page_num < total_pages:
            time.sleep(1)
    
    if all_data:
        # Save to both CSV and JSON
        save_to_csv(all_data, 'Data/bio_medical_engineering.csv')
        save_to_json(all_data, 'Data/bio_medical_engineering.json')
        print(f"\n{'='*50}")
        print(f"Successfully scraped {len(all_data)} institutions from {total_pages} page(s)")
        if total_count:
            print(f"Expected: {total_count} institutions")
        print(f"{'='*50}")
    else:
        print("\nNo data was scraped. Please check the URL and try again.")


if __name__ == '__main__':
    main()
