from google.adk.agents import LlmAgent,SequentialAgent
from HisabAgent.tools.receipt_parser import parse_receipt_agent  # corrected function name
from HisabAgent.tools.wallet_creator import generate_wallet_pass
from HisabAgent.prompts.instructions import COMBINED_INSTRUCTION,GREET_INSTRUCTION,COORDINATOR_INSTRUCTION,DASHBOARD_PROMPT
from HisabAgent.tools.anomolytool import detect_anomalies_for_user
from HisabAgent.tools.RecurringExpenseTool import detect_recurring_expenses
from HisabAgent.tools.TrendTool import get_category_trends
from HisabAgent.tools.CoreAggregatorTool import aggregate_user_monthly_data
from HisabAgent.tools.TimeSlotTool import analyze_time_slots

# ─── ReceiptAgent: Parses receipt image using OCR + Gemini
process_input=LlmAgent(
    name="WalletFlowAgent",
    model="gemini-2.5-flash",
    description="Handles the complete flow of receipt parsing and wallet pass generation.",
    instruction=COMBINED_INSTRUCTION,
    tools=[parse_receipt_agent, generate_wallet_pass])

# ─── GreetingAgent: Handles small talk, polite replies
greeting_agent = LlmAgent(
    name="GreetingAgent",
    model="gemini-2.5-flash",
    instruction=GREET_INSTRUCTION
)
insight_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="UnifiedInsightAgent",
    description="Performs full receipt analysis including trends, anomalies, time slots, recurring items, and aggregates.",
    instruction=DASHBOARD_PROMPT,
    tools=[
        aggregate_user_monthly_data,
        get_category_trends,
        detect_recurring_expenses,
        detect_anomalies_for_user,
        analyze_time_slots
    ],
    output_key="insight_text"
)

# ─── Coordinator: Root agent routes requests to the appropriate sub-agent
root_agent = LlmAgent(
    name="Coordinator",
    model="gemini-2.5-flash",
    description="Routes user input to appropriate sub-agents.",
    instruction=COORDINATOR_INSTRUCTION,
    sub_agents=[greeting_agent, process_input,insight_agent]
)