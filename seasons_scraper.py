import asyncio
import re
from playwright.async_api import async_playwright
import os
import sqlite3

BASE_URL = "https://www.basketball-reference.com"
BROWSER_CONFIGS = {
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "viewport": {"width": 1366, "height": 768},
    "locale": "en-US",
    "extra_http_headers": {"Accept-Language": "en-US,en;q=0.9"}
}
SEASONS = {
    "2019-20": 2020,
    "2020-21": 2021,
    "2021-22": 2022,
    "2022-23": 2023,
    "2023-24": 2024,
}


def team_code_from_href(href):
    m = re.search(r'/teams/([A-Z]{3})/', href or "")
    return m.group(1) if m else None


def player_id_from_href(href):
    m = re.search(r'/players/[a-z]/([a-zA-Z0-9]+)\.html', href or "")
    return m.group(1) if m else None


async def get_playoffs_data(page, year):
    """Winner, loser, and Finals MVP from the playoffs summary page (exact structure shown in screenshot)."""
    await page.goto(f"{BASE_URL}/playoffs/NBA_{year}.html", wait_until="domcontentloaded", timeout=30000)
    
    result = await page.evaluate("""() => {
        let championHref = null;
        let runnerUpHref = null;
        let fmvpHref = null;

        const metaPs = document.querySelectorAll("#meta p");
        for (const p of metaPs) {
            if (p.textContent.includes("Finals MVP")) {
                const a = p.querySelector('a[href*="/players/"]');
                if (a) {
                    fmvpHref = a.getAttribute("href");
                    break;
                }
            }
        }

        let table = document.querySelector("table#all_playoffs");
        if (!table) {
            const container = document.querySelector("#all_all_playoffs");
            const comment = container && Array.from(container.childNodes).find(n => n.nodeType === 8);
            if (comment) {
                const wrapper = document.createElement("div");
                wrapper.innerHTML = comment.nodeValue;
                table = wrapper.querySelector("table");
            }
        }

        if (table) {
            for (const row of table.querySelectorAll("tbody tr")) {
                if (row.innerText.includes("Finals") && !row.innerText.includes("Conference")) {
                    const links = Array.from(row.querySelectorAll('a[href*="/teams/"]')).map(a => a.getAttribute("href"));
                    if (links.length >= 2) {
                        championHref = links[0];
                        runnerUpHref = links[1];
                    }
                    break;
                }
            }
        }

        return { championHref, runnerUpHref, fmvpHref };
    }""")

    champion = team_code_from_href(result["championHref"])
    runner_up = team_code_from_href(result["runnerUpHref"])
    finals_mvp = player_id_from_href(result["fmvpHref"])
    
    return champion, runner_up, finals_mvp


async def get_mvp_award(page, year):
    """Regular Season MVP winner directly from the awards page."""
    await page.goto(f"{BASE_URL}/awards/awards_{year}.html", wait_until="domcontentloaded", timeout=30000)
    
    href = await page.evaluate("""() => {
        const mvpTable = document.querySelector("table#mvp");
        if (mvpTable) {
            const link = mvpTable.querySelector("tbody tr a[href*='/players/']");
            return link ? link.getAttribute("href") : null;
        }
        return null;
    }""")
    
    return player_id_from_href(href)


async def get_league_avg_pts(page, year):
    """League average points from the main league page."""
    await page.goto(f"{BASE_URL}/leagues/NBA_{year}.html", wait_until="domcontentloaded", timeout=30000)
    
    pts = await page.evaluate("""() => {
        const table = document.querySelector("table#per_game-team");
        if (table) {
            const row = table.querySelector("tfoot tr") || Array.from(table.querySelectorAll("tr")).find(r => r.innerText.includes("League Average"));
            if (row) {
                const el = row.querySelector('[data-stat="pts"]');
                return el ? el.innerText.trim() : null;
            }
        }
        return null;
    }""")
    
    try:
        return float(pts)
    except (TypeError, ValueError):
        return None


async def scrape_season(page, season_name, year):
    champion, runner_up, finals_mvp = await get_playoffs_data(page, year)
    await asyncio.sleep(1)
    
    mvp = await get_mvp_award(page, year)
    await asyncio.sleep(1)
    
    league_avg_pts = await get_league_avg_pts(page, year)
    await asyncio.sleep(1)

    season_row = {
        "season_id": year,
        "season_name": season_name,
        "champion_id": champion,
        "runner_up_id": runner_up,
        "league_avg_pts": league_avg_pts,
        "mvp_player_id": mvp,
        "finals_mvp_player_id": finals_mvp,
    }

    print(f"{season_name}: champion={champion}, runner_up={runner_up}, league_avg_pts={league_avg_pts}, mvp={mvp}, finals_mvp={finals_mvp}")
    return season_row


async def main():
    all_seasons = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="chrome")
        context = await browser.new_context(**BROWSER_CONFIGS)
        page = await context.new_page()

        for season_name, year in SEASONS.items():
            all_seasons.append(await scrape_season(page, season_name, year))

        await browser.close()
        
    script_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(script_dir, "basketball.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
   
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS seasons (
            season_id INTEGER PRIMARY KEY,
            season_name TEXT,
            champion_id TEXT,
            runner_up_id TEXT,
            league_avg_pts REAL,
            mvp_player_id TEXT,
            finals_mvp_player_id TEXT
        )
    """)

    for row in all_seasons:
        cursor.execute("""
            INSERT OR REPLACE INTO seasons VALUES (
                :season_id, :season_name, :champion_id, :runner_up_id, 
                :league_avg_pts, :mvp_player_id, :finals_mvp_player_id
            )
        """, row)
        
    conn.commit()
    conn.close()
    print("داده‌ها با موفقیت در basketball.db ذخیره شدند!")
    return all_seasons


if __name__ == "__main__":
    asyncio.run(main())