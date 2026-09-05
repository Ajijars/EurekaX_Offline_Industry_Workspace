import asyncio
import httpx
import os
from pathlib import Path

# URLs for datasets
DATASETS = {
    "chinook.sqlite": "https://github.com/lerocha/chinook-database/raw/master/ChinookDatabase/DataSources/Chinook_Sqlite.sqlite",
    "california_housing.csv": "https://raw.githubusercontent.com/ageron/handson-ml/master/datasets/housing/housing.csv",
    "dummy_products.json": "https://dummyjson.com/products?limit=100",
}

async def download_file(client, url, dest):
    print(f"Downloading {dest} from {url}...")
    try:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
        with open(dest, 'wb') as f:
            f.write(response.content)
        print(f"[SUCCESS] Saved {dest}")
    except Exception as e:
        print(f"[ERROR] Failed to download {dest}: {e}")

async def main():
    target_dir = Path("data") / "real_datasets"
    target_dir.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient() as client:
        tasks = []
        for filename, url in DATASETS.items():
            dest = target_dir / filename
            tasks.append(download_file(client, url, dest))
        
        await asyncio.gather(*tasks)
        
    print("\nDownload complete. Datasets saved to data/real_datasets/")

if __name__ == "__main__":
    asyncio.run(main())
