import asyncio
import re
from datetime import datetime, date
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup, Comment
from models import Player, Team
import sqlite3

BASE_URL = "https://www.basketball-reference.com"

BROWSER_CONFIGS = {
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "viewport": {"width": 1366, "height": 768},
    "locale": "en-US",
    "extra_http_headers": {"Accept-Language": "en-US,en;q=0.9"}
}

MULTI_WORD_CITIES = ["New York", "Los Angeles", "Golden State", "Oklahoma City", "San Antonio", "New Orleans"]

# مشخص کردن state
TEAM_STATES = {
    "ATL": "Georgia", "BOS": "Massachusetts", "BRK": "New York",
    "CHO": "North Carolina", "CHI": "Illinois", "CLE": "Ohio",
    "DAL": "Texas", "DEN": "Colorado", "DET": "Michigan",
    "GSW": "California", "HOU": "Texas", "IND": "Indiana",
    "LAC": "California", "LAL": "California", "MEM": "Tennessee",
    "MIA": "Florida", "MIL": "Wisconsin", "MIN": "Minnesota",
    "NOP": "Louisiana", "NYK": "New York", "OKC": "Oklahoma",
    "ORL": "Florida", "PHI": "Pennsylvania", "PHO": "Arizona",
    "POR": "Oregon", "SAC": "California", "SAS": "Texas",
    "TOR": "Ontario", "UTA": "Utah", "WAS": "Washington D.C."
}

DATABASE = "basketball_reference.db"

def log(message) -> None:
    print(f"[Players & Teams Scraper] {message}", flush=True)

def parse_team_name(full_name: str) -> tuple[str, str]:
    for city in MULTI_WORD_CITIES:
        if full_name.startswith(city):
            return city, full_name[len(city):].strip()
    parts = full_name.split()
    return (parts[0], " ".join(parts[1:]) if len(parts) > 1 else full_name)

def parse_height_to_cm(height_str: str) -> int:
    try:
        match = re.search(r"(\d+)-(\d+)", height_str)
        if match:
            ft, inches = map(int, match.groups())
            total_inches = (ft * 12) + inches
            return round(total_inches * 2.54)
    except Exception as e:
        log(e)
    return 0

def parse_weight_to_kg(weight_str: str) -> int:
    try:
        clean = weight_str.lower().replace("lb", "").strip().replace(",", "")
        if clean.isdigit():
            return round(int(clean) * 0.453592)
    except Exception as e:
        log(e)
    return 0

async def scrape_player_profile(page, href: str) -> Player:
    try:
        await page.goto(f"{BASE_URL}{href}", wait_until="domcontentloaded", timeout=60000)
        meta = page.locator("#meta")
        if await meta.count() == 0: return None
        
        name = (await meta.locator("h1").inner_text()).strip()
        birthdate = None
        birth_span = meta.locator("span#necro-birth")
        if await birth_span.count() == 0:
            birth_span = meta.locator("span#birth")
            
        if await birth_span.count() > 0:
            birth_data = await birth_span.get_attribute("data-birth")
            if birth_data:
                try: birthdate = datetime.strptime(birth_data.strip(), "%Y-%m-%d").date()
                except Exception as e:
                    log(e)
        
        height, weight = 0, 0
        meta_text = await meta.inner_text()
        
        spans = meta.locator("span")
        for i in range(await spans.count()):
            txt = (await spans.nth(i).inner_text()).strip()
            if re.match(r"^\d+-\d+$", txt): height = parse_height_to_cm(txt)
            elif "lb" in txt: weight = parse_weight_to_kg(txt)

        nationality = "US"
        nat_link = meta.locator("a[href*='/friv/birthplaces.fcgi']")
        if await nat_link.count() > 0: nationality = (await nat_link.first.inner_text()).strip()

        shoots = "Right"
        shoots_match = re.search(r"Shoots:\s*([A-Za-z]+)", meta_text)
        if shoots_match: shoots = shoots_match.group(1)
            
        college = "N/A"
        college_link = meta.locator("a[href*='/friv/colleges.fcgi']")
        if await college_link.count() > 0: college = (await college_link.first.inner_text()).strip()
            
        position = []
        pos_match = re.search(r"Position:\s*([^\n]+)", meta_text)
        if pos_match:
            pos_text = pos_match.group(1)
            for pos in ["Point Guard", "Shooting Guard", "Small Forward", "Power Forward", "Guard", "Forward", "Center"]:
                if pos in pos_text and pos not in position: position.append(pos)
        if not position: position = ["Forward"]

        player_id = href.split("/")[-1].replace(".html", "")
        birthdate = birthdate.strftime("%Y-%m-%d") if birthdate else "1970-01-01"
        height_cm = height if height > 0 else None
        weight_kg = weight if weight > 0 else None
        # Create and return player object
        player = Player(player_id, name, birthdate, height_cm, weight_kg, shoots,
                        nationality, college, position)
        return player
    except Exception as e:
        log(f"خطا در پروفایل بازیکن {href}: {e}")
    return None

async def scrape_multi_season_data(start_year: int, end_year: int) -> tuple[list[Player], list[Team]]:
    log("در حال راه‌اندازی مرورگر...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(**BROWSER_CONFIGS)
        page = await context.new_page()
        
        all_players_data = []
        all_teams_data = []
        processed_players = Player.get_player_ids()
        processed_teams = Team.get_team_ids()
        
        for season_year in range(start_year, end_year + 1):
            log(f"\n=شروع استخراج فصل {season_year} =")
            season_url = f"{BASE_URL}/leagues/NBA_{season_year}.html"
            
            try:
                await page.goto(season_url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(3000)
                
                content = await page.content()
                soup = BeautifulSoup(content, 'html.parser')
                
                confs_div = soup.find('div', id='all_standings')
                if confs_div:
                    for comment in confs_div.find_all(string=lambda text: isinstance(text, Comment)):
                        if 'table' in comment:
                            c_soup = BeautifulSoup(comment, 'html.parser')
                            for a in c_soup.find_all('a', href=re.compile(rf'/teams/[A-Z]{{3}}/{season_year}\.html')):
                                t_code = a.get('href').split('/')[-2]
                                if t_code not in processed_teams:
                                    processed_teams.add(t_code)
                                    city, t_name = parse_team_name(a.text.strip())
                                    state = TEAM_STATES.get(t_code, "N/A")
                                    # Create and append team object
                                    team = Team(t_code, t_name, city, state)
                                    all_teams_data.append(team)
                                    log(f"   موفق: تیم {team.name} ثبت شد.")
                                    
                    for a in confs_div.find_all('a', href=re.compile(rf'/teams/[A-Z]{{3}}/{season_year}\.html')):
                        t_code = a.get('href').split('/')[-2]
                        if t_code not in processed_teams:
                            processed_teams.add(t_code)
                            city, t_name = parse_team_name(a.text.strip())
                            state = TEAM_STATES.get(t_code, "N/A")
                            # Create and append team object
                            team = Team(t_code, t_name, city, state)
                            all_teams_data.append(team)
                            log(f"   موفق: تیم {team.name} ثبت شد.")

                team_hrefs = set()
                season_pattern = re.compile(rf'/teams/[A-Z]{{3}}/{season_year}\.html')
                if confs_div:
                    for comment in confs_div.find_all(string=lambda text: isinstance(text, Comment)):
                        if 'table' in comment:
                            for link in BeautifulSoup(comment, 'html.parser').find_all('a', href=season_pattern):
                                team_hrefs.add(link.get('href'))
                    for link in confs_div.find_all('a', href=season_pattern):
                        team_hrefs.add(link.get('href'))
                if not team_hrefs:
                    for link in soup.find_all('a', href=season_pattern): team_hrefs.add(link.get('href'))

                team_hrefs = list(team_hrefs)
                log(f"تعداد {len(team_hrefs)} تیم در فصل {season_year} پیدا شد.")

                for t_idx, team_href in enumerate(team_hrefs, 1):
                    team_url = f"{BASE_URL}{team_href}"
                    team_code = team_href.split('/')[-2]
                    log(f"--- [{t_idx}/{len(team_hrefs)}] فصل {season_year} | تیم {team_code} ---")
                    
                    try:
                        await page.goto(team_url, wait_until="domcontentloaded", timeout=60000)
                        player_locators = page.locator('table#roster tbody tr td[data-stat="player"] a')
                        
                        player_hrefs = []
                        for i in range(await player_locators.count()):
                            href = await player_locators.nth(i).get_attribute("href")
                            if href and href not in player_hrefs: player_hrefs.append(href)
                        
                        for p_idx, p_href in enumerate(player_hrefs, 1):
                            p_id = p_href.split("/")[-1].replace(".html", "")
                            if p_id in processed_players: continue
                                
                            log(f"   [{p_idx}/{len(player_hrefs)}] استخراج: {p_id}")
                            profile = await scrape_player_profile(page, p_href)
                            if profile:
                                all_players_data.append(profile)
                                processed_players.add(p_id)
                                log(f"   موفق: بازیکن {profile.name} ثبت شد.")
                            await asyncio.sleep(2)
                    except Exception as e:
                        log(f"خطا در تیم {team_code}: {e}")
            except Exception as e:
                log(f"خطا در فصل {season_year}: {e}")
                
        await context.close()
        await browser.close()
        
        log(f"\n==================== پایان عملیات استخراج ====================")
        log(f"تعداد کل تیم‌های منحصربه‌فرد ثبت شده: {len(all_teams_data)}")
        log(f"تعداد کل بازیکنان منحصربه‌فرد ثبت شده: {len(all_players_data)}")
        return (all_players_data, all_teams_data)

def insert_data(players: list[Player], teams: list[Team]) -> None:
    """Insert players and teams into database"""
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        # Insert players into database
        for player in players:
            player.insert_player(cursor)
        # Insert teams into database
        for team in teams:
            team.insert_team(cursor)
        # Commit changes and close connection
        conn.commit()
        conn.close()
    except Exception as e:
        log(f"خطا در وارد کردن دیتا به دیتابیس: {e}")

async def main():
    players, teams = await scrape_multi_season_data(2019, 2024)
    insert_data(players, teams)
    if players:
        print(f"نمونه ساختار بازیکن : {players[0]}")
    if teams:
        print(f"نمونه ساختار تیم     : {teams[0]}")

if __name__ == "__main__":
    asyncio.run(main())