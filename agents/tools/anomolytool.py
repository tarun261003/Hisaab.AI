from typing import Dict, List
from datetime import datetime
from collections import defaultdict
from statistics import mean, stdev
from google.cloud import firestore

db = firestore.Client()

def detect_anomalies_for_user(uid: str) -> Dict:
    """
    Detect spending anomalies for a given user's receipts.
    Uses mean and standard deviation across total spends and item categories.
    """
    txs = db.collection("users").document(uid).collection("transactions").stream()

    all_receipts = []
    category_spend = defaultdict(list)

    for doc in txs:
        receipt = doc.to_dict()
        total = sum(item["amount"] for item in receipt.get("items", []))
        receipt["total_spend"] = total
        all_receipts.append(receipt)

        for item in receipt.get("items", []):
            category_spend[item["category"]].append(item["amount"])

    total_spends = [r["total_spend"] for r in all_receipts]
    if len(total_spends) < 2:
        return {"message": "Not enough data for anomaly detection."}

    mean_total = mean(total_spends)
    std_total = stdev(total_spends)
    category_avg = {cat: mean(amts) for cat, amts in category_spend.items()}

    anomalies = []

    for receipt in all_receipts:
        if receipt["total_spend"] > mean_total + 2 * std_total:
            anomaly_categories = []
            for item in receipt.get("items", []):
                avg = category_avg.get(item["category"], 0)
                if avg > 0 and item["amount"] > 1.5 * avg:
                    anomaly_categories.append({
                        "name": item["name"],
                        "category": item["category"],
                        "amount": item["amount"],
                        "avg_category_amount": round(avg, 2)
                    })

            anomalies.append({
                "receipt_id": receipt["receipt_id"],
                "timestamp": receipt["timestamp"].isoformat(),
                "merchant": receipt["merchant"],
                "total_spend": receipt["total_spend"],
                "anomaly_reason": f"High total spend (>{round(mean_total + 2 * std_total, 2)})",
                "category_anomalies": anomaly_categories
            })

    return {
        "uid": uid,
        "detected_at": datetime.now().isoformat(),
        "anomalies": anomalies
    }

# 🧪 Example usage
if __name__ == "__main__":
    uid = "demo_user_id"
    result = detect_anomalies_for_user(uid)
    print(result)
