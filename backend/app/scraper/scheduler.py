import threading
from datetime import datetime

class CrawlerScheduler:
    def __init__(self):
        self.last_run = None
        self.is_running = False
        self.results = []

    def run_crawler(self):
        from app.scraper.crawler_official import crawl_all, sync_to_db, update_latest_prices
        self.is_running = True
        self.last_run = datetime.now()
        try:
            cars = crawl_all()
            db_result = sync_to_db(cars) if cars else {"updated": 0, "added": 0, "total_in_db": 0}
            price_updated = update_latest_prices()
            result = {
                "timestamp": self.last_run.isoformat(),
                "cars_crawled": len(cars),
                "db_updated": db_result["updated"],
                "db_added": db_result["added"],
                "prices_refreshed": price_updated,
                "total_in_db": db_result["total_in_db"],
                "status": "success"
            }
        except Exception as e:
            result = {"timestamp": self.last_run.isoformat(), "error": str(e), "status": "error"}
        self.results.append(result)
        self.is_running = False
        return result

    def run_in_background(self):
        if self.is_running:
            return {"status": "already_running"}
        t = threading.Thread(target=self.run_crawler, daemon=True)
        t.start()
        return {"status": "started", "timestamp": datetime.now().isoformat()}

    def get_status(self):
        return {
            "is_running": self.is_running,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "total_runs": len(self.results),
            "last_result": self.results[-1] if self.results else None,
        }

scheduler = CrawlerScheduler()
