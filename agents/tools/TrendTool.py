from typing import Dict
from datetime import datetime
from google.cloud import firestore

db = firestore.Client()

def get_category_trends(uid: str, year: int, month: int) -> Dict:
    """
    Compare category spend for the current and previous month.
    """

    def get_doc(y, m):
        doc_id = f"{y}-{m:02}"
        doc_ref = db.collection("users").document(uid).collection("analytics").document(doc_id)
        doc = doc_ref.get()
        return doc.to_dict() if doc.exists else {}

    # Fetch current and previous month data
    this_data = get_doc(year, month).get("category_totals", {})

    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    last_data = get_doc(prev_year, prev_month).get("category_totals", {})

    # Build trend map
    trends = {}
    all_categories = set(this_data) | set(last_data)

    for cat in all_categories:
        curr = this_data.get(cat, 0)
        prev = last_data.get(cat, 0)
        change = curr - prev
        percent = (change / prev * 100) if prev != 0 else (100.0 if curr != 0 else 0.0)

        trends[cat] = {
            "previous": round(prev, 2),
            "current": round(curr, 2),
            "change": round(change, 2),
            "percent_change": round(percent, 2)
        }

    return {
        "uid": uid,
        "month": f"{year}-{month:02}",
        "trend_summary": trends,
        "generated_at": datetime.now().isoformat()
    }

# 🧪 Example usage
if __name__ == "__main__":
    print(get_category_trends("demo_user", 2024, 7))
