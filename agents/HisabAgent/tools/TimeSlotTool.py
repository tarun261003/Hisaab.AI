from typing import Dict
from datetime import datetime
from collections import defaultdict
from google.cloud import firestore

db = firestore.Client()

def analyze_time_slots(uid: str) -> Dict:
    """
    Analyze total spend per time slot (morning, afternoon, evening, night).
    """
    txs = db.collection("users").document(uid).collection("transactions").stream()

    slot_totals = defaultdict(float)

    for doc in txs:
        receipt = doc.to_dict()
        timestamp = receipt.get("timestamp")

        if not isinstance(timestamp, datetime):
            timestamp = datetime.fromisoformat(timestamp)

        hour = timestamp.hour
        total = sum(item["amount"] for item in receipt.get("items", []))

        if 5 <= hour < 12:
            slot = "morning"
        elif 12 <= hour < 17:
            slot = "afternoon"
        elif 17 <= hour < 21:
            slot = "evening"
        else:
            slot = "night"

        slot_totals[slot] += total

    return {
        "uid": uid,
        "slot_summary": dict(slot_totals),
        "generated_at": datetime.now().isoformat()
    }

# 🧪 Example usage
if __name__ == "__main__":
    result = analyze_time_slots("demo_user_id")
    print(result)
