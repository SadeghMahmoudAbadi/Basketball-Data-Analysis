import asyncio
from playwright.async_api import async_playwright
from models import Award, AwardSeason
import sqlite3

BASE_URL = "https://www.basketball-reference.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
}

AWARDS_MAP = {
    "mvp": {"name": "Michael Jordan Trophy", "table_id": "table#mvp"},
    "dpoy": {"name": "Hakeem Olajuwon Trophy", "table_id": "table#dpoy"},
    "roy": {"name": "Wilt Chamberlain Trophy", "table_id": "table#roy"},
    "smoy": {"name": "John Havlicek Trophy", "table_id": "table#smoy"},
    "mip": {"name": "George Mikan Trophy", "table_id": "table#mip"}
}

DATABASE = "basketball_reference.db"

def log(message) -> None:
    print(f"[Awards Scraper] {message}", flush=True)

async def safe_goto(page, url: str, retries: int = 4, delay: int = 7) -> bool:
    for attempt in range(retries):
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            return True
        except Exception as e:
            log(f"خطا در بارگذاری {url} (تلاش {attempt + 1}). صبر به مدت {delay} ثانیه...")
            await asyncio.sleep(delay)
    return False

async def scrape_nba_awards_data(start_year: int, end_year: int) -> tuple[list[Award], list[AwardSeason]]:
    log("در حال راه‌اندازی مرورگر برای بخش جوایز...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(user_agent=HEADERS["User-Agent"])
        page = await context.new_page()
        # Store awards in awards_list
        awards_list = []
        for award_id, info in AWARDS_MAP.items():
            awards_list.append(Award(award_id, info['name']))
        # Store season awards in award_seasons_list
        award_seasons_list = []
        for year in range(start_year, end_year + 1):
            awards_url = f"{BASE_URL}/awards/awards_{year}.html"
            log(f"در حال استخراج جوایز فصل {year}...")
            
            if await safe_goto(page, awards_url):
                for a_id, info in AWARDS_MAP.items():
                    rows = page.locator(f"{info['table_id']} tbody tr")
                    rows_count = await rows.count()
                    
                    for i in range(rows_count):
                        player_link = rows.nth(i).locator('td[data-stat="player"] a')
                        if await player_link.count() > 0:
                            href = await player_link.get_attribute("href")
                            p_id = href.split("/")[-1].replace(".html", "")
                            award_seasons_list.append(AwardSeason(year, a_id, p_id))
                
                await asyncio.sleep(2)
            else:
                log(f"خطای جدی: موفق به باز کردن صفحه جوایز سال {year} نشدیم.")
        
        await browser.close()
        return (awards_list, award_seasons_list)

def insert_data(awards: list[Award], award_season_list: list[AwardSeason]) -> None:
    """Insert coaches and coach_stats into database"""
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        # Insert coaches into database
        for award in awards:
            award.insert_award(cursor)
        # Insert coach_stats into database
        for award_season in award_season_list:
            award_season.insert_award_season(cursor)
        # Commit changes and close connection
        conn.commit()
        conn.close()
    except Exception as e:
        log(f"خطا در وارد کردن دیتا به دیتابیس: {e}")

async def main():
    awards, award_seasons = await scrape_nba_awards_data(2019, 2024)
    insert_data(awards, award_seasons)
    log(f"\n==================== پایان عملیات جوایز ====================")
    log(f"تعداد کل انواع جوایز تعریف شده: {len(awards)}")
    log(f"تعداد کل رکوردهای ثبت شده (رابطه بازیکن-جایزه-سال): {len(award_seasons)}")
    
    if award_seasons:
        log(f"نمونه رکورد اول: {award_seasons[0]}")

if __name__ == "__main__":
    asyncio.run(main())