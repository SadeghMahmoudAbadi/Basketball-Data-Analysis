# Basketball Data Analysis

An NBA data collection and analysis project using **Python, Playwright, SQLite, Pandas, SciPy, Matplotlib, and Seaborn**.

The project collects data from **Basketball-Reference** for the **2019–20 to 2023–24 NBA seasons**, stores it in SQLite, and performs statistical analysis on players, teams, coaches, and awards.

## Project Structure

```text
├── *_Scraper.py       # Collect NBA data
├── create_database.py # Create database tables
├── models.py          # Database models
├── analysis.ipynb     # Data analysis and visualizations
└── *.db               # SQLite databases
```

### Scrapers

* **Seasons** — season champions, MVPs, Finals MVPs, and league averages
* **Players** — player profiles and team information
* **Player Stats** — traditional and advanced player statistics
* **Team Stats** — wins, losses, ratings, pace, and playoff results
* **Coaches** — coach profiles and records
* **Awards** — major NBA award winners

## Analysis

`analysis.ipynb` uses SQL, Pandas, and statistical methods to explore topics such as:

* The relationship between **Net Rating and wins**
* Player performance and team success
* Scoring dependency and team wins
* Differences between player positions
* American vs. international players
* Age, playing time, and player characteristics

The notebook also includes visualizations and hypothesis tests.

## Installation

```bash
git clone https://github.com/SadeghMahmoudAbadi/Basketball-Data-Analysis.git
cd Basketball-Data-Analysis

pip install pandas numpy scipy matplotlib seaborn beautifulsoup4 playwright
playwright install
```

## Usage

Create the database:

```bash
python create_database.py
```

Run the scrapers:

```bash
python seasons_scraper.py
python Players_Scraper.py
python PlayerStats_Scraper.py
python team_stats_scraper.py
python Coaches_Scraper.py
python Awards_Scraper.py
```

Then open `analysis.ipynb` with Jupyter Notebook to reproduce the analysis.

## Data Pipeline

```text
Basketball-Reference
        ↓
     Scrapers
        ↓
   SQLite Database
        ↓
  SQL + Pandas
        ↓
Statistical Analysis
        ↓
  Visualizations
```

## Notes

The scrapers depend on Basketball-Reference's website structure, so changes to the website may require code updates.
