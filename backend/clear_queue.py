from database import get_reports_collection
col = get_reports_collection()
res = col.update_many({"status": "Queued"}, {"$set": {"status": "Failed"}})
print(f"Updated {res.modified_count} stuck reports.")
