# TrackerCG

TrackerCG is a fullstack web application designed for managing personal Trading Card Game (TCG) collections, supporting games like Magic: The Gathering, Yu-Gi-Oh!, and Pokémon. 

The system automatically extracts real-time market values from external sources to calculate the total value of the user's inventory through a simplified graphical interface.

## Core Features

- **Automated Data Extraction:** Web scraping and consolidation of market data.
- **Inventory Management:** Web dashboard to search, view, and register new cards into the local inventory.
- **Dynamic Valuation:** Calculates the total value of the deck or collection based on current market prices.
- **Persistent Storage:** Local catalog system for the user's collection.

## Tech Stack

- **Backend & API:** Python, FastAPI
- **Data Extraction (Scraping):** BeautifulSoup4, Playwright
- **Database:** SQLite managed via SQLModel
- **Frontend:** HTML5, CSS3, Vanilla JavaScript, Jinja2 Templates
- **Styling:** Tailwind CSS (via CDN)