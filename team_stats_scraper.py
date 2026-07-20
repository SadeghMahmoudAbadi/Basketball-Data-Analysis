import asyncio
import re
from playwright.async_api import async_playwright

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

ROUNDS = ["Missed Playoffs", "First Round", "Conference Semifinals", "Conference Finals", "Finals"]


def to_int(x):
    try:
        return int(x)
    except (ValueError, TypeError):
        return 0


def to_float(x):
    try:
        return float(x)
    except (ValueError, TypeError):
        return 0.0


def team_code_from_href(href):
    m = re.search(r'/teams/([A-Z]{3})/', href or "")
    return m.group(1) if m else None


async def get_team_ratings(page, year):
    """W, L, ORtg, DRtg, Pace for every team from the 'advanced-team' table."""
    await page.goto(f"{BASE_URL}/leagues/NBA_{year}.html", wait_until="domcontentloaded")

    rows = await page.evaluate("""() => {
        const table = document.querySelector("table#advanced-team");
        if (!table) return [];
        const val = (row, stat) => {
            const el = row.querySelector(`[data-stat="${stat}"]`);
            return el ? el.innerText.trim() : "";
        };
        return Array.from(table.querySelectorAll("tbody tr")).map(row => {
            const link = row.querySelector('[data-stat="team"] a');
            if (!link) return null;
            return {
                href: link.getAttribute("href"),
                wins: val(row, "wins"),
                losses: val(row, "losses"),
                off_rtg: val(row, "off_rtg"),
                def_rtg: val(row, "def_rtg"),
                pace: val(row, "pace"),
            };
        }).filter(r => r !== null);
    }""")

    result = {}
    for row in rows:
        code = team_code_from_href(row["href"])
        if code:
            result[code] = row
    return result


async def get_division_ranks(page, year):
    """Rank of each team within its division (from divs_standings_E / divs_standings_W)."""
    await page.goto(f"{BASE_URL}/leagues/NBA_{year}.html", wait_until="domcontentloaded")

    rows = await page.evaluate("""() => {
        const result = [];
        ["divs_standings_E", "divs_standings_W"].forEach(id => {
            const table = document.querySelector(`table#${id}`);
            if (!table) return;
            let rank = 0;
            table.querySelectorAll("tbody tr").forEach(row => {
                const link = row.querySelector('[data-stat="team_name"] a');
                if (!link) { rank = 0; return; }  // division header row
                rank += 1;
                result.push({ href: link.getAttribute("href"), rank });
            });
        });
        return result;
    }""")

    return {team_code_from_href(r["href"]): r["rank"] for r in rows if team_code_from_href(r["href"])}


async def get_playoff_results(page, year):
    """Furthest playoff round reached by each team, parsed from the (comment-hidden) playoffs table."""
    await page.goto(f"{BASE_URL}/playoffs/NBA_{year}.html", wait_until="domcontentloaded", timeout=30000)

    debug = await page.evaluate("""() => {
        let table = document.querySelector("table#all_playoffs");
        let source = "direct";

        if (!table) {
            const container = document.querySelector("#all_all_playoffs");
            if (!container) return { step: "no container" };
            const comment = Array.from(container.childNodes).find(n => n.nodeType === 8);
            if (!comment) return { step: "no comment inside container" };
            const wrapper = document.createElement("div");
            wrapper.innerHTML = comment.nodeValue;
            table = wrapper.querySelector("table");
            source = "comment";
            if (!table) return { step: "no table inside comment" };
        }

        const rows = Array.from(table.querySelectorAll("tbody tr")).map(row => ({
            text: row.innerText,
            hrefs: Array.from(row.querySelectorAll('a[href*="/teams/"]')).map(a => a.getAttribute("href")),
        }));
        return { step: "ok", source, rows };
    }""")

    if debug["step"] != "ok":
        return {}

    series = debug["rows"]

    results = {}
    for s in series:
        round_name = next((r for r in reversed(ROUNDS) if r != "Finals" and r in s["text"]), None)
        if round_name is None and "Finals" in s["text"]:
            round_name = "Finals"
        if not round_name:
            continue
        for href in s["hrefs"]:
            code = team_code_from_href(href)
            if not code:
                continue
            best_so_far = results.get(code, "Missed Playoffs")
            if ROUNDS.index(round_name) > ROUNDS.index(best_so_far):
                results[code] = round_name
    return results


async def scrape_season(page, season_name, year):
    ratings = await get_team_ratings(page, year)
    await asyncio.sleep(1)
    ranks = await get_division_ranks(page, year)
    await asyncio.sleep(1)
    playoffs = await get_playoff_results(page, year)
    await asyncio.sleep(1)

    season_stats = []
    for team_code, r in ratings.items():
        wins, losses = to_int(r["wins"]), to_int(r["losses"])
        off_rtg, def_rtg = to_float(r["off_rtg"]), to_float(r["def_rtg"])

        season_stats.append({
            "season_id": year,
            "team_id": team_code,
            "wins": wins,
            "losses": losses,
            "win_loss_percent": round(wins / (wins + losses), 3) if (wins + losses) else 0.0,
            "finish_rank": ranks.get(team_code, 0),
            "playoff_result": playoffs.get(team_code, "Missed Playoffs"),
            "offensive_rating": off_rtg,
            "defensive_rating": def_rtg,
            "net_rating": round(off_rtg - def_rtg, 1),
            "pace": to_float(r["pace"]),
        })

    print(f"{season_name}: {len(season_stats)} teams")
    return season_stats

async def main():
    all_stats = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, channel="chrome")
        context = await browser.new_context(**BROWSER_CONFIGS)
        page = await context.new_page()

        for season_name, year in SEASONS.items():
            all_stats += await scrape_season(page, season_name, year)

        await browser.close()

    return all_stats


if __name__ == "__main__":
    asyncio.run(main())