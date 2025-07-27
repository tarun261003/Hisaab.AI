from typing import Dict, Tuple
from datetime import datetime
from collections import defaultdict
from google.cloud import firestore

db = firestore.Client()

def detect_recurring_expenses(uid: str) -> Dict:
    """
    Detect recurring expense items across months.
    An item is considered recurring if it appears in at least 2 different months.
    """
    txs = db.collection("users").document(uid).collection("transactions").stream()

    recurring_tracker: Dict[Tuple[str, str], Dict] = defaultdict(lambda: {
        "months": set(),
        "total_amount": 0.0,
        "occurrences": 0
    })

    for doc in txs:
        receipt = doc.to_dict()
        month_id = receipt["timestamp"].strftime("%Y-%m")

        for item in receipt.get("items", []):
            key = (item["name"].lower().strip(), item["category"].lower().strip())
            recurring_tracker[key]["months"].add(month_id)
            recurring_tracker[key]["total_amount"] += item["amount"]
            recurring_tracker[key]["occurrences"] += 1

    recurring_items = []
    for (name, category), data in recurring_tracker.items():
        if len(data["months"]) >= 2:
            recurring_items.append({
                "name": name,
                "category": category,
                "months_appeared": sorted(data["months"]),
                "total_amount": round(data["total_amount"], 2),
                "average_amount": round(data["total_amount"] / data["occurrences"], 2)
            })

    return {
        "uid": uid,
        "detected_at": datetime.now().isoformat(),
        "recurring_items": recurring_items
    }

# 🧪 Example usage
if __name__ == "__main__":
    result = detect_recurring_expenses("demo_user_id")
    print(result)
