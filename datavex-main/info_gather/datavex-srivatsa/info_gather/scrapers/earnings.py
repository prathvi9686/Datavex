"""
Earnings Transcript Scraper
Sources:
  1. SEC EDGAR full-text search (free, no API key needed)
  2. Company IR page heuristic crawl
  3. Yahoo Finance earnings summary
"""
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from loguru import logger
from utils.http import safe_get, get_session, extract_text_from_pdf_bytes


EDGAR_SEARCH = "https://efts.sec.gov/LATEST/search-index?q=%22earnings+call%22&dateRange=custom&startdt={start}&enddt={end}&entity={ticker}&forms=8-K"
EDGAR_FILING  = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=8-K&dateb=&owner=include&count=10&search_text="


def search_edgar_transcripts(ticker: str, limit: int = 4) -> list[dict]:
    """
    Fetch 8-K filings from SEC EDGAR for a ticker.
    8-K filings often contain earnings call press releases & transcripts.
    Returns list of dicts with {quarter, raw_text, source_url}
    """
    results = []
    url = EDGAR_FILING.format(ticker=ticker.upper())
    session = get_session()
    try:
        resp = safe_get(url, session)
        soup = BeautifulSoup(resp.text, "lxml")

        # Find filing links
        filing_links = []
        for row in soup.select("table.tableFile2 tr"):
            cells = row.find_all("td")
            if len(cells) >= 2 and "8-K" in cells[0].get_text():
                link_tag = cells[1].find("a")
                if link_tag:
                    filing_links.append("https://www.sec.gov" + link_tag["href"])
            if len(filing_links) >= limit:
                break

        for filing_url in filing_links:
            text, source = _extract_text_from_filing_page(filing_url, session)
            if text:
                results.append({
                    "quarter": _guess_quarter_from_text(text),
                    "raw_text": text,
                    "source_url": source
                })

    except Exception as e:
        logger.warning(f"EDGAR scrape failed for {ticker}: {e}")

    return results


def _extract_text_from_filing_page(filing_index_url: str, session) -> tuple[str, str]:
    """Given an 8-K filing index page, find and return the main document text."""
    try:
        resp = safe_get(filing_index_url, session)
        soup = BeautifulSoup(resp.text, "lxml")
        # Filing index has a table listing documents
        for link in soup.select("table a"):
            href = link.get("href", "")
            name = link.get_text(strip=True).lower()
            # Look for the primary document (htm or txt)
            if href.endswith((".htm", ".html", ".txt")) and "8-k" not in name:
                doc_url = urljoin("https://www.sec.gov", href)
                doc_resp = safe_get(doc_url, session)
                doc_soup = BeautifulSoup(doc_resp.text, "lxml")
                text = doc_soup.get_text(separator=" ", strip=True)
                if len(text) > 500:
                    return text[:50000], doc_url   # cap at 50k chars
    except Exception as e:
        logger.debug(f"Filing extraction failed: {e}")
    return "", filing_index_url


def scrape_ir_page_transcripts(ir_url: str, company_name: str) -> list[dict]:
    """
    Crawl a company's Investor Relations page looking for:
    - Earnings transcript links
    - PDF presentations
    Returns list of dicts.
    """
    results = []
    session = get_session()
    try:
        resp = safe_get(ir_url, session)
        soup = BeautifulSoup(resp.text, "lxml")

        keyword_patterns = re.compile(
            r"(earnings|transcript|quarterly|annual.report|investor.presentation|10-[kq])",
            re.I
        )
        for link in soup.find_all("a", href=True):
            text = link.get_text(strip=True)
            href = link["href"]
            full_url = urljoin(ir_url, href)

            if not keyword_patterns.search(text + href):
                continue

            if href.lower().endswith(".pdf"):
                try:
                    pdf_resp = safe_get(full_url, session)
                    raw_text = extract_text_from_pdf_bytes(pdf_resp.content)
                    results.append({
                        "quarter": _guess_quarter_from_text(raw_text),
                        "raw_text": raw_text[:50000],
                        "source_url": full_url,
                    })
                    logger.info(f"[{company_name}] PDF transcript pulled: {full_url}")
                except Exception as e:
                    logger.debug(f"PDF failed: {e}")

            elif href.lower().endswith((".htm", ".html")):
                try:
                    page_resp = safe_get(full_url, session)
                    page_soup = BeautifulSoup(page_resp.text, "lxml")
                    raw_text = page_soup.get_text(separator=" ", strip=True)
                    if len(raw_text) > 1000:
                        results.append({
                            "quarter": _guess_quarter_from_text(raw_text),
                            "raw_text": raw_text[:50000],
                            "source_url": full_url,
                        })
                        logger.info(f"[{company_name}] HTML transcript pulled: {full_url}")
                except Exception as e:
                    logger.debug(f"HTML failed: {e}")

            if len(results) >= 6:
                break

    except Exception as e:
        logger.warning(f"IR page scrape failed ({ir_url}): {e}")

    return results


def _guess_quarter_from_text(text: str) -> str:
    """Heuristically extract quarter/year string from transcript text."""
    match = re.search(r"(Q[1-4]\s*20\d{2}|20\d{2}\s*Q[1-4]|FY\s*20\d{2})", text, re.I)
    if match:
        return match.group(0).strip()
    year_match = re.search(r"(20\d{2})", text)
    return year_match.group(0) if year_match else "Unknown"
