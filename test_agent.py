import asyncio
import httpx
import json
import sqlite3
import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from app.auth.security import create_access_token

async def test_agent():
    # Get admin user ID from DB
    conn = sqlite3.connect("data/eurekax.db")
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE role='admin' LIMIT 1")
    admin_id = c.fetchone()[0]
    conn.close()
    
    # Generate token
    token = create_access_token({"sub": admin_id})
    print(f"Generated Token for Admin ID {admin_id}: {token[:10]}...")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        # Call agent
        headers = {"Authorization": f"Bearer {token}"}
        print("Sending prompt to Agent...")
        agent_res = await client.post("http://127.0.0.1:8000/api/agent/run", json={
            "query": "What is the name of the Track with TrackId 1 in Chinook? Also, what is the median house value in the california housing dataset?",
            "mode": "agent"
        }, headers=headers)
        
        print("Status:", agent_res.status_code)
        print("Response:", json.dumps(agent_res.json(), indent=2))

if __name__ == "__main__":
    asyncio.run(test_agent())
