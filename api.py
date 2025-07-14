from fastapi import FastAPI, Query, HTTPException
from pathlib import Path
import json
import subprocess
import uvicorn
import os
import shutil 

app = FastAPI()

OUTPUT_DIR = Path('output')
OUTPUT_DIR_FILES = ["data.json", "images.json", "links.json", "initial_links.json"]

OUTPUT_DIR_FILES_1 = ["data.json"]

# Ensure the output directory exists and is clean before each scrape
def setup_output_directory():
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        for file in OUTPUT_DIR_FILES_1:
            path = OUTPUT_DIR / file
            with open(path, 'w', encoding='utf-8') as f:
                f.write('[]')

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True) 

@app.get("/scrape")
async def scrape(url: str = Query(..., description="URL to scrape")):
    setup_output_directory() 
    try:
        subprocess.run(["scrapy", "crawl", "quotes_spider", "-a", f"start_url={url}"],)
        result = read_scraped_data()
        return result
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Scrapy process failed: {e.stderr}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

@app.get("/scrape/depth1")
async def scrape_depth_1(
    url: str = Query(..., description="URL to scrape"),
    depth: int = Query(..., description="Depth for scraping"),
    ):
    setup_output_directory()
    try:
        # Run the Scrapy spider for depth 1
        subprocess.run(
            ["scrapy", "crawl", "quotes_spider_depth1", "-a", f"start_url={url}", "-a", f"depth={depth}"],
            check=True,
            capture_output=True,
            text=True,
        )
        result = read_scraped_data()
        return result
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Scrapy process failed: {e.stderr}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

def read_scraped_data():
    result = {"data.json": []}

    for file in OUTPUT_DIR_FILES_1:
        path = OUTPUT_DIR / file
        with path.open(encoding='utf-8') as f:
            result[file] = json.load(f)

    return result

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)