from datetime import datetime
from agents.tools import anomolytool, CoreAggregatorTool, RecurringExpenseTool, TimeSlotTool, TrendTool

# 🔧 Inject mock receipts
mock_receipts = [
    {
        "receipt_id": "r123",
        "uid": "user_001",
        "timestamp": datetime.fromisoformat("2025-07-24T10:45:00"),
        "merchant": "Big Bazaar",
        "category_summary": {"groceries": 520.0, "household": 75.5},
        "items": [
            {"name": "Milk", "category": "groceries", "amount": 60},
            {"name": "Detergent", "category": "household", "amount": 75.5},
            {"name": "Rice", "category": "groceries", "amount": 460}
        ]
    },
    {
        "receipt_id": "r124",
        "uid": "user_001",
        "timestamp": datetime.fromisoformat("2025-07-20T18:30:00"),
        "merchant": "D-Mart",
        "category_summary": {"groceries": 160.0, "personal care": 40},
        "items": [
            {"name": "Apples", "category": "groceries", "amount": 120},
            {"name": "Toothpaste", "category": "personal care", "amount": 40}
        ]
    },
    {
        "receipt_id": "r125",
        "uid": "user_001",
        "timestamp": datetime.fromisoformat("2025-07-10T21:00:00"),
        "merchant": "Amazon",
        "category_summary": {"electronics": 8500},
        "items": [
            {"name": "Printer", "category": "electronics", "amount": 8500}
        ]
    }
]

# 📊 Manually invoke each tool with mock_receipts
uid = "user_001"
year = 2025
month = 7

# Each tool must expose a callable that supports mock receipts
dashboard_metrics = CoreAggregatorTool.aggregate_user_monthly_data(uid, year, month, receipts=mock_receipts)
trend_summary = TrendTool.get_category_trends(uid, year, month, receipts=mock_receipts)
recurring_items = RecurringExpenseTool.detect_recurring_expenses(uid, receipts=mock_receipts)
anomalies = anomolytool.detect_anomalies_for_user(uid, receipts=mock_receipts)
slot_summary = TimeSlotTool.analyze_time_slots(uid, receipts=mock_receipts)

# Combine result as final "agent output"
final_state = {
    "dashboard_metrics": dashboard_metrics,
    "trend_insights": trend_summary,
    "recurring_items": recurring_items,
    "anomalies": anomalies,
    "slot_summary": slot_summary,
}

# 🖨️ Print final output
print("\n✅ Final Insight Output:\n")
for key, value in final_state.items():
    print(f"{key.upper()}:\n{value}\n")
