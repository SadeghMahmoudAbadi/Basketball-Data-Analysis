import asyncio
import re
from urllib.parse import urljoin
from datetime import datetime, date
from playwright.async_api import async_playwright
from models import Coach, CoachStats
import sqlite3

BASE_URL = "https://www.basketball-reference.com"

BROWSER_CONFIGS = {
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "viewport": {"width": 1366, "height": 768},
    "locale": "en-US",
    "extra_http_headers": {"Accept-Language": "en-US,en;q=0.9"}
}

DATABASE = "basketball_reference.db"

def log(message) -> None:
    print(f"[Coaches Scraper] {message}", flush=True)

def convert_to_date_object(date_text: str) -> date:
    try:
        dt = datetime.strptime(re.sub(r'\s+', ' ', date_text).strip(), "%B %d, %Y")
        return dt.date()
    except:
        return None

def get_target_seasons() -> list[dict]:
    target_years = {
        "2019-20": 2020,
        "2020-21": 2021,
        "2021-22": 2022,
        "2022-23": 2023,
        "2023-24": 2024
    }
    return [{"season": name, "url": f"{BASE_URL}/leagues/NBA_{year}.html"} for name, year in target_years.items()]

async def get_teams_of_season(page, season_url) -> list[dict]:
    await page.goto(season_url, wait_until="domcontentloaded")
    team_links_locator = page.locator('th[data-stat="team_name"] a')
    teams = []
    seen_teams = set()
    count = await team_links_locator.count()
    
    for index in range(count):
        link = team_links_locator.nth(index)
        href = await link.get_attribute("href")
        match = re.search(r'/teams/([A-Z]{3})/', href)
        if match:
            team_code = match.group(1)
            if team_code not in seen_teams:
                seen_teams.add(team_code)
                teams.append({"team_code": team_code, "url": urljoin(BASE_URL, href)})
    return teams

async def scrape_coach_profile(page, href: str) -> Coach:
    try:
        await page.goto(f"{BASE_URL}{href}", wait_until="domcontentloaded", timeout=30000)
        meta = page.locator("#meta")
        if await meta.count() == 0: return None
        
        meta_text = await meta.inner_text()
        name = (await meta.locator("h1").inner_text()).strip()
        
        birthdate = None
        birth_match = re.search(r"Born:\s*([A-Za-z]+\s+\d+,\s+\d{4})", meta_text)
        if birth_match: birthdate = convert_to_date_object(birth_match.group(1))
            
        nationality = "US"
        if "Born:" in meta_text:
            nat_match = re.search(r"Born:\s*[A-Za-z]+\s+\d+,\s+\d{4}\s+in\s+([A-Za-z\s,]+)", meta_text)
            if nat_match: nationality = nat_match.group(1).split(",")[-1].strip()

        coach_id = href.split("/")[-1].replace(".html", "")
        birthdate = birthdate.strftime("%Y-%m-%d") if birthdate else "1970-01-01"
        # Create and return coach object
        coach = Coach(coach_id, name, birthdate, nationality)
        return coach
    except Exception as e:
        log(f"خطا در بررسی پروفایل مربی {href}: {e}")
    return None

async def scrape_coaches_data() -> tuple[list[Coach], list[CoachStats]]:
    log("در حال راه‌اندازی مرورگر...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(**BROWSER_CONFIGS)
        page = await context.new_page()
        
        seasons = get_target_seasons()
        coaches_stats = []
        all_coach_hrefs = set()
        seen_coaches = set()
        coaches_profiles = []
        
        for s in seasons:
            current_season = s["season"]
            log(f"\n======== شروع استخراج تیم‌های فصل: {current_season} ========")
            teams = await get_teams_of_season(page, s["url"])
            log(f"تعداد {len(teams)} تیم پیدا شد. در حال استخراج مربیان...")
            
            for t in teams:
                try:
                    await page.goto(t["url"], wait_until="domcontentloaded", timeout=45000)
                    coach_paragraph = page.locator('div#meta p:has-text("Coach:")')
                    
                    if await coach_paragraph.count() > 0:
                        coach_links = coach_paragraph.locator('a')
                        links_count = await coach_links.count()
                        
                        for l_idx in range(links_count):
                            link = coach_links.nth(l_idx)
                            coach_href = await link.get_attribute("href")
                            
                            if "/coaches/" in coach_href:
                                coach_id = coach_href.split("/")[-1].replace(".html", "")
                                all_coach_hrefs.add(coach_href)
                                
                                p_text = await coach_paragraph.inner_text()
                                wins, losses = 0, 0
                                record_match = re.search(r'(\d+)-(\d+)', p_text)
                                if record_match:
                                    wins = int(record_match.group(1))
                                    losses = int(record_match.group(2))
                                # Create and append coach_stat object
                                coach_stat = CoachStats(current_season, coach_id, t["team_code"], wins, losses)
                                coaches_stats.append(coach_stat)
                except Exception as e:
                    log(f"خطا در اسکن مربی تیم {t['team_code']}: {e}")
                
                await page.wait_for_timeout(3000)
            
        log(f"\nشروع استخراج مشخصات فردی مربیان یکتا (تعداد کل مربیان: {len(all_coach_hrefs)}) ...")
        for c_href in all_coach_hrefs:
            c_id = c_href.split("/")[-1].replace(".html", "")
            if c_id not in seen_coaches:
                log(f"   -> در حال اسکن پروفایل: {c_id}")
                profile = await scrape_coach_profile(page, c_href)
                if profile:
                    coaches_profiles.append(profile)
                    seen_coaches.add(c_id)
                await page.wait_for_timeout(3500)
        
        await context.close()
        await browser.close()

        return (coaches_profiles, coaches_stats)
    
def insert_data(coaches: list[Coach], coach_stats: list[CoachStats]) -> None:
    """Insert coaches and coach_stats into database"""
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        # Insert coaches into database
        for coach in coaches:
            coach.insert_coach(cursor)
        # Insert coach_stats into database
        for stats in coach_stats:
            stats.insert_coach_stats(cursor)
        # Commit changes and close connection
        conn.commit()
        conn.close()
    except Exception as e:
        log(f"خطا در وارد کردن دیتا به دیتابیس: {e}")

async def main():
    coaches_profiles, coaches_stats = await scrape_coaches_data()
    insert_data(coaches_profiles, coaches_stats)
    print("\n========== گزارش نهایی دیتای مربیان ==========")
    print(f"۱. تعداد کل پروفایل مربیان (تیبل ۱): {len(coaches_profiles)}")
    print(f"۲. تعداد رکورد آمار فصلی مربیان (تیبل ۲): {len(coaches_stats)}")

if __name__ == "__main__":
    asyncio.run(main())