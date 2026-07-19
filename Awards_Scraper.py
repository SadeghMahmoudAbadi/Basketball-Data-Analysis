import asyncio
import re
from datetime import datetime, date
from playwright.async_api import async_playwright

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

MULTI_WORD_CITIES = ["New York", "Los Angeles", "Golden State", "Oklahoma City", "San Antonio", "New Orleans"]

def parse_team_name(full_name: str):
    for city in MULTI_WORD_CITIES:
        if full_name.startswith(city):
            return city, full_name[len(city):].strip()
    parts = full_name.split()
    return parts[0], " ".join(parts[1:]) if len(parts) > 1 else full_name

def parse_height_to_inches(height_str: str) -> int:
    try:
        match = re.search(r"(\d+)-(\d+)", height_str)
        if match:
            ft, inches = map(int, match.groups())
            return (ft * 12) + inches
    except: pass
    return 0

def convert_to_date_object(date_text: str) -> date:
    try:
        clean_text = re.sub(r'\s+', ' ', date_text).strip()
        dt = datetime.strptime(clean_text, "%B %d, %Y")
        return dt.date()
    except: return None

async def safe_goto(page, url: str, retries: int = 4, delay: int = 7) -> bool:
    for attempt in range(retries):
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=60000)
            return True
        except Exception as e:
            await asyncio.sleep(delay)
    return False

async def scrape_person_profile(page, href: str) -> dict:
    if not await safe_goto(page, f"{BASE_URL}{href}"): return None
    try:
        meta = page.locator("#meta")
        meta_text = await meta.inner_text()
        name = (await meta.locator("h1").inner_text()).strip()
        
        birthdate = None
        birth_match = re.search(r"Born:\s*([A-Za-z]+\s+\d+,\s+\d{4})", meta_text)
        if birth_match: birthdate = convert_to_date_object(birth_match.group(1))
        
        player_id = href.split("/")[-1].replace(".html", "")
        return {"player_id": player_id, "name": name, "birthdate": birthdate}
    except: return None

async def scrape_nba_raw_data(start_year: int, end_year: int):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(user_agent=HEADERS["User-Agent"])
        page = await context.new_page()
        
        awards_list = [{"award_id": a_id, "name": info["name"]} for a_id, info in AWARDS_MAP.items()]
        award_seasons_list, teams_list, seasons_list = [], [], []
        players_list = []
        seen_teams, seen_players = set(), set()

        for year in range(start_year, end_year + 1):
            league_url = f"{BASE_URL}/leagues/NBA_{year}.html"
            if not await safe_goto(page, league_url): continue
            
            # استخراج تیم‌ها
            team_links = page.locator('th[data-stat="team_name"] a')
            for i in range(await team_links.count()):
                link = team_links.nth(i)
                href = await link.get_attribute("href")
                full_name = (await link.inner_text()).strip()
                code_match = re.search(r'/teams/([A-Z]{3})/', href)
                if code_match and code_match.group(1) not in seen_teams:
                    seen_teams.add(code_match.group(1))
                    city, name = parse_team_name(full_name)
                    teams_list.append({"team_id": code_match.group(1), "name": name, "city": city})

            # استخراج جوایز و بازیکنان
            awards_url = f"{BASE_URL}/awards/awards_{year}.html"
            if await safe_goto(page, awards_url):
                for a_id, info in AWARDS_MAP.items():
                    rows = page.locator(f"{info['table_id']} tbody tr")
                    for i in range(await rows.count()):
                        player_link = rows.nth(i).locator('td[data-stat="player"] a')
                        if await player_link.count() > 0:
                            href = await player_link.get_attribute("href")
                            p_id = href.split("/")[-1].replace(".html", "")
                            award_seasons_list.append({"season_id": year, "award_id": a_id, "player_id": p_id})
                            if p_id not in seen_players:
                                seen_players.add(p_id)
                                p_data = await scrape_person_profile(page, href)
                                if p_data: players_list.append(p_data)
        
        await browser.close()
        return awards_list, award_seasons_list, teams_list, players_list

async def main():
    awards, award_seasons, teams, players = await scrape_nba_raw_data(2019, 2024)
    print(f"تعداد تیم‌ها: {len(teams)} | تعداد بازیکنان: {len(players)}")

if __name__ == "__main__":
    asyncio.run(main())