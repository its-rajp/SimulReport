from database import get_reports_collection
from google.cloud.firestore_v1.base_query import FieldFilter

def clear_queue():
    col = get_reports_collection()
    docs = col.where(filter=FieldFilter("status", "==", "Queued")).stream()
    
    count = 0
    for doc in docs:
        doc.reference.update({"status": "Failed"})
        count += 1
        
    print(f"Updated {count} stuck reports.")

if __name__ == "__main__":
    clear_queue()
