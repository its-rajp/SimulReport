import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
import database

col = database.get_reports_collection()
print("Latest 5 reports in MongoDB:")
for doc in col.find().sort("created_at", -1).limit(5):
    print("-" * 50)
    print(f"ID: {doc['_id']}")
    print(f"Project: {doc.get('project_name')}")
    print(f"Industry: {doc.get('industry')}")
    print(f"Service: {doc.get('service')}")
    print(f"Status: {doc.get('status')}")
    print(f"Error: {doc.get('error')}")
    print(f"Created At: {doc.get('created_at')}")
    print(f"File Path: {doc.get('file_path')}")
