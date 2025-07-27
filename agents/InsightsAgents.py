# agent_pipeline.py

from google.adk.agents import LlmAgent, SequentialAgent
from agents.tools.anomolytool import detect_anomalies_for_user
from agents.tools.RecurringExpenseTool import detect_recurring_expenses
from agents.tools.TrendTool import get_category_trends
from agents.tools.CoreAggregatorTool import aggregate_user_monthly_data
from agents.tools.TimeSlotTool import analyze_time_slots

# --- Core Aggregator Agent ---
core_aggregator_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="CoreAggregatorAgent",
    description="Aggregates core spending metrics from receipts.",
    instruction="""
You are a financial metrics extractor. Use the `aggregator_tool` to compute:
- total_spend
- category_breakdown
- top_categories
- daily_series
- receipt_count
- average_per_receipt

Store results in a dashboard_metrics JSON. Use the tool to perform calculations and output clear results.
""",
    tools=[aggregate_user_monthly_data],
    output_key="dashboard_metrics"
)

# --- Trend Agent ---
trend_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="TrendAgent",
    description="Analyzes month-over-month spending trends.",
    instruction="""
You are a trend analysis agent. Use the `trend_tool` to identify changes in user spending from previous to current month. Output a structured trend_insights JSON with:
- percentage increase/decrease per category
- significant rising or falling trends
""",
    tools=[get_category_trends],
    output_key="trend_insights"
)

# --- Recurring Expense Agent ---
recurring_expense_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="RecurringExpenseAgent",
    description="Detects recurring monthly expenses from receipts.",
    instruction="""
You are a recurring expense analyzer. Use the `recurring_tool` to detect:
- Monthly repeating merchants
- Subscription-like patterns
Output in recurring_expenses JSON format.
""",
    tools=[detect_recurring_expenses],
    output_key="recurring_expenses"
)

# --- Anomaly Detection Agent ---
anomaly_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="AnomalyAgent",
    description="Detects abnormal spending patterns.",
    instruction="""
You are a financial anomaly detector. Use the `anomaly_tool` to find:
- Unusual spikes in expense
- Category-level outliers
Store output in spending_anomalies JSON format.
""",
    tools=[detect_anomalies_for_user],
    output_key="spending_anomalies"
)

# --- Time Slot Agent ---
time_slot_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="TimeSlotAgent",
    description="Breaks down expenses by time of day.",
    instruction="""
You are a time-slot breakdown analyzer. Use the `time_slot_tool` to analyze spending by:
- Morning (5 AM – 12 PM)
- Afternoon (12 PM – 5 PM)
- Evening (5 PM – 9 PM)
- Night (9 PM – 5 AM)
Output the data into a time_slot_breakdown JSON.
""",
    tools=[analyze_time_slots],
    output_key="time_slot_breakdown"
)

# --- Insight Agent (Final Text Output) ---
insight_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="InsightAgent",
    description="Generates a human-readable summary from all computed metrics.",
    instruction="""
You are an insight summarizer. Use the following state keys:
- {dashboard_metrics}
- {trend_insights}
- {recurring_expenses}
- {spending_anomalies}
- {time_slot_breakdown}

Write a concise, friendly summary for the user. Mention notable changes, anomalies, and recurring expenses. End with an overall financial health statement.Take the uid as anonymous while calling tools.
""",
    output_key="insight_text"
)

# --- Main Sequential Pipeline Agent ---
root_agent = SequentialAgent(
    name="DashboardPipelineAgent",
    description="Executes a complete spending pattern analysis in order.",
    sub_agents=[
        core_aggregator_agent,
        trend_agent,
        recurring_expense_agent,
        anomaly_agent,
        time_slot_agent,
        insight_agent
    ]
)