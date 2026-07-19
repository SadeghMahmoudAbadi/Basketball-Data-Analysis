import asyncio
import re
from datetime import datetime, date
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup, Comment

BASE_URL = "https://www.basketball-reference.com"

BROWSER_CONFIGS = {
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "viewport": {"width": 1366, "height": 768},
    "locale": "en-US",
    "extra_http_headers": {"Accept-Language": "en-US,en;q=0.9"}
}

def log(message):
    print(f"[Players Scraper] {message}", flush=True)

def parse_height_to_inches(height_str: str) -> int:
    try:
        match = re.search(r"(\d+)-(\d+)", height_str)
        if match:
            ft, inches = map(int, match.groups())
            return (ft * 12) + inches
    except:
        pass
    return 0

def to_int(val: str, default: int = 0) -> int:
    if not val:
        return default
    clean = val.strip().replace(",", "")
    return int(clean) if clean.isdigit() or (clean.startswith('-') and clean[1:].isdigit()) else default

async def scrape_player_profile(page, href: str):
    try:
        await page.goto(f"{BASE_URL}{href}", wait_until="domcontentloaded", timeout=60000)
        
        meta = page.locator("#meta")
        if await meta.count() == 0: 
            return None
        
        name = (await meta.locator("h1").inner_text()).strip()
        
        birthdate = None
        birth_span = meta.locator("span#necro-birth")
        if await birth_span.count() == 0:
            birth_span = meta.locator("span#birth")
            
        if await birth_span.count() > 0:
            birth_data = await birth_span.get_attribute("data-birth")
            if birth_data:
                try:
                    birthdate = datetime.strptime(birth_data.strip(), "%Y-%m-%d").date()
                except:
                    pass
        
        height, weight = 0, 0
        meta_text = await meta.inner_text()
        
        spans = meta.locator("span")
        span_count = await spans.count()
        for i in range(span_count):
            txt = await spans.nth(i).inner_text()
            if re.match(r"^\d+-\d+$", txt.strip()):
                height = parse_height_to_inches(txt.strip())
            elif "lb" in txt:
                weight = to_int(txt.replace("lb", ""))

        nationality = "US"
        nat_link = meta.locator("a[href*='/friv/birthplaces.fcgi']")
        if await nat_link.count() > 0:
            nationality = (await nat_link.first.inner_text()).strip()

        shoots = "Right"
        shoots_match = re.search(r"Shoots:\s*([A-Za-z]+)", meta_text)
        if shoots_match: 
            shoots = shoots_match.group(1)
            
        college = "N/A"
        college_link = meta.locator("a[href*='/friv/colleges.fcgi']")
        if await college_link.count() > 0:
            college = (await college_link.first.inner_text()).strip()
            
        position = []
        pos_match = re.search(r"Position:\s*([^\n]+)", meta_text)
        if pos_match:
            pos_text = pos_match.group(1)
            for pos in ["Guard", "Forward", "Center", "Point Guard", "Shooting Guard", "Small Forward", "Power Forward"]:
                if pos in pos_text and pos not in position:
                    position.append(pos)
        if not position: 
            position = ["Forward"]

        player_id = href.split("/")[-1].replace(".html", "")
        
        return {
            "player_id": player_id,
            "name": name,
            "birthdate": birthdate if birthdate else date(1990, 1, 1),
            "height": height,
            "weight": weight,
            "shoots": shoots,
            "nationality": nationality,
            "college": college,
            "position": position
        }
    except Exception as e:
        log(f"خطا در بررسی پروفایل بازیکن {href}: {e}")
    return None

async def scrape_multi_season_players(start_year: int, end_year: int):
    log("در حال راه‌اندازی مرورگر...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(**BROWSER_CONFIGS)
        page = await context.new_page()
        
        all_players_data = []
        processed_players = set()
        
        for season_year in range(start_year, end_year + 1):
            log(f"\n==================== شروع استخراج فصل {season_year} ====================")
            
            season_url = f"{BASE_URL}/leagues/NBA_{season_year}.html"
            try:

                await page.goto(season_url, wait_until="commit", timeout=60000)
                await page.wait_for_timeout(3000)
                
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                team_hrefs = set()
                
                comments = soup.find_all(string=lambda text: isinstance(text, Comment))
                for comment in comments:
                    if 'table' in comment and ('teams' in comment or 'team' in comment):
                        comment_soup = BeautifulSoup(comment, 'html.parser')
                        # پیدا کردن همه لینک‌های تیم‌ها بر اساس ساختار ادرس دهی سایت
                        links = comment_soup.find_all('a', href=re.compile(r'/teams/[A-Z]{3}/\d{4}\.html'))
                        for link in links:
                            team_hrefs.add(link.get('href'))
                
                if not team_hrefs:
                    links = soup.find_all('a', href=re.compile(r'/teams/[A-Z]{3}/\d{4}\.html'))
                    for link in links:
                        team_hrefs.add(link.get('href'))

                team_hrefs = list(team_hrefs)
                log(f"تعداد {len(team_hrefs)} تیم در فصل {season_year} پیدا شد.")
                
                if len(team_hrefs) == 0:
                     log(" محتوای صفحه تیم‌ها لود نشد.")
                     continue

                for t_idx, team_href in enumerate(team_hrefs, 1):
                    team_url = f"{BASE_URL}{team_href}"
                    team_code = team_href.split('/')[-2]
                    log(f"--- [{t_idx}/{len(team_hrefs)}] فصل {season_year} | تیم {team_code} ---")
                    
                    try:
                        await page.goto(team_url, wait_until="domcontentloaded", timeout=60000)
                        player_locators = page.locator('table#roster tbody tr td[data-stat="player"] a')
                        player_count = await player_locators.count()
                        
                        player_hrefs = []
                        for i in range(player_count):
                            href = await player_locators.nth(i).get_attribute("href")
                            if href and href not in player_hrefs:
                                player_hrefs.append(href)
                        
                        for p_idx, p_href in enumerate(player_hrefs, 1):
                            p_id = p_href.split("/")[-1].replace(".html", "")
                            
                            if p_id in processed_players:
                                continue
                                
                            log(f"   [{p_idx}/{len(player_hrefs)}] استخراج مشخصات: {p_id}")
                            profile = await scrape_player_profile(page, p_href)
                            
                            if profile:
                                all_players_data.append(profile)
                                processed_players.add(p_id)
                                log(f"   موفق: {profile['name']} ثبت شد.")
                            
                            await asyncio.sleep(2)
                            
                    except Exception as e:
                        log(f"خطا در پردازش تیم {team_code} در سال {season_year}: {e}")
                        
            except Exception as e:
                log(f"خطا در باز کردن صفحه اصلی فصل {season_year}: {e}")
                
        await context.close()
        await browser.close()
        
        print("\n" + "="*20 + f" پایان کل فرآیند: {len(all_players_data)} بازیکن منحصربه‌فرد ثبت شدند " + "="*20)

if __name__ == "__main__":
    asyncio.run(scrape_multi_season_players(2019, 2024))