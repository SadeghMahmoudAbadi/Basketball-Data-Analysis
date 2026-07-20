import asyncio
import re
from urllib.parse import urljoin
from playwright.async_api import async_playwright
from models import PlayerStats
import sqlite3

BASE_URL = "https://www.basketball-reference.com"

BROWSER_CONFIGS = {
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "viewport": {"width": 1366, "height": 768},
    "locale": "en-US",
    "extra_http_headers": {"Accept-Language": "en-US,en;q=0.9"}
}

DATABASE = "basketball_reference.db"


def log(message):
    print(f"[Players Scraper] {message}", flush=True)

def get_target_seasons():
    return {
        "2019-20": 2020,
        "2020-21": 2021,
        "2021-22": 2022,
        "2022-23": 2023,
        "2023-24": 2024
    }

async def get_teams_of_season(page, year):
    url = f"{BASE_URL}/leagues/NBA_{year}.html"
    await page.goto(url, wait_until="domcontentloaded")
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

async def get_players_from_team_page(page, team_url):
    try:
        await page.goto(team_url, wait_until="domcontentloaded", timeout=30000)
        players_data = await page.evaluate("""() => {
            const rows = document.querySelectorAll("table#roster tbody tr");
            const result = [];
            rows.forEach(row => {
                const playerLink = row.querySelector('td[data-stat="player"] a');
                const expEl = row.querySelector('td[data-stat="years_experience"]');
                if (playerLink) {
                    result.push({
                        href: playerLink.getAttribute("href"),
                        xp: expEl ? expEl.innerText.trim() : "0"
                    });
                }
            });
            return result;
        }""")
        return players_data
    except Exception as e:
        log(f"خطا در استخراج بازیکنان تیم: {e}")
        return []

async def scrape_player_totals(page, player_href, player_xp, target_years):
    player_id = player_href.split("/")[-1].replace(".html", "")
    player_stats_list = []
    
    try:
        await page.goto(f"{BASE_URL}{player_href}", wait_until="domcontentloaded", timeout=30000)
        
        if await page.locator("table#totals_stats").count() == 0:
            return []

        rows_data = await page.evaluate("""() => {
            const headerCells = document.querySelectorAll("table#totals_stats thead tr th");
            let trpDblIndex = -1;
            headerCells.forEach((cell, index) => {
                const cellText = cell.innerText.trim();
                if (cellText === "Trp-Dbl" || cell.getAttribute("data-stat") === "trp_dbl") {
                    trpDblIndex = index;
                }
            });

            const advRows = document.querySelectorAll("table#advanced tbody tr");
            const wsMap = {};
            advRows.forEach(row => {
                if (row.classList.contains('thead')) return;
                const yearEl = row.querySelector('th[data-stat="year_id"]');
                const teamEl = row.querySelector('td[data-stat="team_name_abbr"]');
                const wsEl = row.querySelector('td[data-stat="ws"]');
                if (yearEl && teamEl && wsEl) {
                    const key = yearEl.innerText.trim() + "_" + teamEl.innerText.trim();
                    wsMap[key] = wsEl.innerText.trim();
                }
            });

            const rows = document.querySelectorAll("table#totals_stats tbody tr");
            const data = [];
            rows.forEach(row => {
                if (row.classList.contains('thead')) return;
                
                const yearEl = row.querySelector('th[data-stat="year_id"]');
                if (!yearEl) return;
                
                const getVal = (selector) => {
                    const el = row.querySelector(`td[data-stat="${selector}"]`);
                    return el ? el.innerText.trim() : "";
                };

                const seasonText = yearEl.innerText.trim();
                const teamId = getVal("team_name_abbr");
                const wsKey = seasonText + "_" + teamId;

                let trpDblVal = "0";
                if (trpDblIndex !== -1) {
                    const allCells = row.querySelectorAll("th, td");
                    if (allCells[trpDblIndex]) {
                        trpDblVal = allCells[trpDblIndex].innerText.trim();
                    }
                }
                
                if (!trpDblVal || trpDblVal === "") {
                    trpDblVal = "0";
                }

                data.push({
                    season_text: seasonText,
                    team_id: teamId,
                    g: getVal("games"),
                    gs: getVal("games_started"),
                    mp: getVal("mp"),
                    fg: getVal("fg"),
                    fga: getVal("fga"),
                    fg_pct: getVal("fg_pct"),
                    three_p: getVal("fg3"),
                    three_pa: getVal("fg3a"),
                    three_p_pct: getVal("fg3_pct"),
                    two_p: getVal("fg2"),
                    two_pa: getVal("fg2a"),
                    two_p_pct: getVal("fg2_pct"),
                    efg_pct: getVal("efg_pct"),
                    ft: getVal("ft"),
                    fta: getVal("fta"),
                    ft_pct: getVal("ft_pct"),
                    orb: getVal("orb"),
                    drb: getVal("drb"),
                    trb: getVal("trb"),
                    ast: getVal("ast"),
                    stl: getVal("stl"),
                    blk: getVal("blk"),
                    tov: getVal("tov"),
                    pf: getVal("pf"),
                    pts: getVal("pts"),
                    trp_dbl: trpDblVal,
                    ws: wsMap[wsKey] || "0.0"
                });
            });
            return data;
        }""")

        for row in rows_data:
            if row["season_text"] not in target_years:
                continue
                
            season_id = target_years[row["season_text"]]
            
            def_int = lambda x: int(x) if x and x.isdigit() else 0
            def_float = lambda x: float(x) if x else 0.0

            stats_obj = PlayerStats(
                season_id=season_id, player_id=player_id, team_id=row["team_id"],
                g=def_int(row["g"]), gs=def_int(row["gs"]), mp=def_int(row["mp"]), 
                fg=def_int(row["fg"]), fga=def_int(row["fga"]), fg_pct=def_float(row["fg_pct"]),
                three_p=def_int(row["three_p"]), three_pa=def_int(row["three_pa"]), three_p_pct=def_float(row["three_p_pct"]),
                two_p=def_int(row["two_p"]), two_pa=def_int(row["two_pa"]), two_p_pct=def_float(row["two_p_pct"]), 
                efg_pct=def_float(row["efg_pct"]),
                ft=def_int(row["ft"]), fta=def_int(row["fta"]), ft_pct=def_float(row["ft_pct"]), 
                orb=def_int(row["orb"]), drb=def_int(row["drb"]), trb=def_int(row["trb"]),
                ast=def_int(row["ast"]), stl=def_int(row["stl"]), blk=def_int(row["blk"]), 
                tov=def_int(row["tov"]), pf=def_int(row["pf"]), pts=def_int(row["pts"]),
                trp_dbl=def_int(row["trp_dbl"]), ws=def_float(row["ws"]), xp=player_xp
            )
            player_stats_list.append(stats_obj)
            
    except Exception as e:
        log(f"خطا در اسکن جدول توتال بازیکن {player_id}: {e}")
        
    return player_stats_list

def insert_data(player_stats: list[PlayerStats]) -> None:
    """Insert player stats into database"""
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        # Insert player stats into database
        for stat in player_stats:
            stat.insert_player_stats(cursor)
        # Commit changes and close connection
        conn.commit()
        conn.close()
    except Exception as e:
        log(f"خطا در وارد کردن دیتا به دیتابیس: {e}")

async def main():
    target_years = get_target_seasons()
    player_registry = {}  
    all_extracted_stats = []

    log("در حال راه‌اندازی مرورگر و جمع‌آوری لیست تمام بازیکنان لیگ...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel='chrome')
        context = await browser.new_context(**BROWSER_CONFIGS)
        page = await context.new_page()
        
        for season_name, year in target_years.items():
            log(f"جمع‌آوری تیم‌های فصل {season_name}...")
            teams = await get_teams_of_season(page, year)
            
            for t in teams:
                log(f"استخراج دیتای بازیکنان تیم {t['team_code']} در فصل {season_name}...")
                players_found = await get_players_from_team_page(page, t["url"])
                for p_info in players_found:
                    href = p_info["href"]
                    player_registry[href] = p_info["xp"]
                
                await asyncio.sleep(1)

        total_players = len(player_registry)
        log(f"\  در مجموع {total_players} بازیکن منحصربه‌فرد پیدا شدند.")
        log("شروع فرآیند اسکریپ کردن جزئیات...")
        
        counter = 0
        for p_href, p_xp in player_registry.items():
            counter += 1
            p_id = p_href.split("/")[-1].replace(".html", "")
            log(f"[{counter}/{total_players}] در حال استخراج آمار بازیکن: {p_id}...")
            
            stats_list = await scrape_player_totals(page, p_href, p_xp, target_years)
            all_extracted_stats.extend(stats_list)
            
            await asyncio.sleep(1.5) 
        await context.close()
        await browser.close()
    

    insert_data(all_extracted_stats)
    log(f"\n در مجموع {len(all_extracted_stats)} رکورد استخراج شد.")

if __name__ == "__main__":
    asyncio.run(main())