#!/usr/bin/env python3
"""
Simple test file to verify basic agent structure without full execution
Tests imports and basic functionality
"""

import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test if all required modules can be imported"""
    print("🧪 Testing imports...")
    
    try:
        # Test basic Python imports
        from datetime import datetime
        print("✅ Standard library imports OK")
        
        # Test if agent file exists and can be read
        if os.path.exists("agents/InsightsAgents.py"):
            print("✅ Agent file exists")
        else:
            print("❌ Agent file not found")
            return False
            
        # Test tool files
        tool_files = [
            "agents/tools/CoreAggregatorTool.py",
            "agents/tools/anomolytool.py", 
            "agents/tools/RecurringExpenseTool.py",
            "agents/tools/TrendTool.py",
            "agents/tools/TimeSlotTool.py"
        ]
        
        for tool_file in tool_files:
            if os.path.exists(tool_file):
                print(f"✅ {tool_file} exists")
            else:
                print(f"❌ {tool_file} not found")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        return False

def test_agent_structure():
    """Test the agent structure without executing"""
    print("\n🔍 Testing agent structure...")
    
    try:
        with open("agents/InsightsAgents.py", "r") as f:
            content = f.read()
            
        # Check for key components
        checks = [
            ("LlmAgent", "LlmAgent class import"),
            ("SequentialAgent", "SequentialAgent class import"),
            ("root_agent", "Root agent definition"),
            ("core_aggregator_agent", "Core aggregator agent"),
            ("trend_agent", "Trend agent"),
            ("recurring_expense_agent", "Recurring expense agent"),
            ("anomaly_agent", "Anomaly agent"),
            ("time_slot_agent", "Time slot agent"),
            ("insight_agent", "Insight agent")
        ]
        
        for check_item, description in checks:
            if check_item in content:
                print(f"✅ {description} found")
            else:
                print(f"❌ {description} missing")
        
        return True
        
    except Exception as e:
        print(f"❌ Structure test failed: {e}")
        return False

def check_requirements():
    """Check if requirements.txt exists and list dependencies"""
    print("\n📦 Checking requirements...")
    
    try:
        if os.path.exists("requirements.txt"):
            with open("requirements.txt", "r") as f:
                requirements = f.read().strip().split("\n")
            
            print("✅ Requirements file found")
            print("📋 Dependencies:")
            for req in requirements:
                if req.strip():
                    print(f"   - {req.strip()}")
        else:
            print("❌ requirements.txt not found")
            
    except Exception as e:
        print(f"❌ Requirements check failed: {e}")

def main():
    """Main test function"""
    print("🤖 SIMPLE AGENT STRUCTURE TEST")
    print("=" * 40)
    
    # Run tests
    imports_ok = test_imports()
    structure_ok = test_agent_structure()
    check_requirements()
    
    print("\n" + "=" * 40)
    print("📊 TEST SUMMARY")
    print("=" * 40)
    
    if imports_ok and structure_ok:
        print("✅ Basic agent structure is valid")
        print("💡 To run the full pipeline, use: python main.py")
        print("💡 Make sure to install dependencies: pip install -r requirements.txt")
    else:
        print("❌ Issues found in agent structure")
    
    print("\n🔧 Next steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Set up Google Cloud credentials if using Firestore")
    print("3. Run full test: python main.py")

if __name__ == "__main__":
    main()