from typing import Dict
from datetime import datetime
from google.cloud import firestore

db = firestore.Client()

def aggregate_user_monthly_data(uid: str, year: int, month: int) -> Dict:
    """
    Aggregate spending data for a specific user and month.
    Computes total spend, daily series, category breakdown, and average per receipt.
    """
    start = datetime(year, month, 1)
    end = datetime(year + (month // 12), (month % 12) + 1, 1)

    txs = db.collection("users").document(uid).collection("transactions") \
        .where("timestamp", ">=", start).where("timestamp", "<", end).stream()

    total_spend = 0.0
    category_breakdown = {}
    daily_series = {}
    receipt_count = 0

    for doc in txs:
        receipt = doc.to_dict()
        receipt_count += 1

        ts = receipt["timestamp"]
        date_str = ts.strftime("%Y-%m-%d")

        day_total = sum(receipt["category_summary"].values())
        daily_series[date_str] = daily_series.get(date_str, 0) + day_total
        total_spend += day_total

        for cat, amt in receipt["category_summary"].items():
            category_breakdown[cat] = category_breakdown.get(cat, 0) + amt

    top_categories = sorted(category_breakdown.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "uid": uid,
        "month": f"{year}-{month:02}",
        "total_spend": round(total_spend, 2),
        "category_breakdown": category_breakdown,
        "top_categories": [cat for cat, _ in top_categories],
        "daily_series": daily_series,
        "receipt_count": receipt_count,
        "average_per_receipt": round(total_spend / receipt_count, 2) if receipt_count else 0.0,
        "generated_at": datetime.now().isoformat()
    }

# 🧪 Example usage
if __name__ == "__main__":
    result = aggregate_user_monthly_data("demo_user_id", 2025, 7)
    print(result)
