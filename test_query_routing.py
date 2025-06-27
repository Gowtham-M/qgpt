#!/usr/bin/env python3
"""
Test script for the intelligent query routing system
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration
API_BASE_URL = "http://localhost:8000"  # Adjust as needed
QUERY_ANALYZE_ENDPOINT = f"{API_BASE_URL}/v1/query/analyze"

# Test queries with expected modes
TEST_QUERIES = [
    {
        "query": "Analyze the area around 37.7749, -122.4194",
        "expected_mode": "Maps",
        "description": "Coordinates-based location query"
    },
    {
        "query": "What's the weather like in New York?",
        "expected_mode": "Basic",
        "description": "General conversational query"
    },
    {
        "query": "What does the contract say about payment terms?",
        "expected_mode": "RAG",
        "description": "Document-specific question"
    },
    {
        "query": "Find all mentions of revenue in the documents",
        "expected_mode": "Search",
        "description": "Document search query"
    },
    {
        "query": "Summarize the main findings from our research",
        "expected_mode": "Summarize",
        "description": "Summarization request"
    },
    {
        "query": "Plan a comprehensive marketing strategy using available tools",
        "expected_mode": "AgenticBot",
        "description": "Complex autonomous task"
    },
    {
        "query": "Calculate the ROI using the financial API",
        "expected_mode": "ToolCalling",
        "description": "External tool usage"
    },
    {
        "query": "Show me places near Central Park",
        "expected_mode": "Maps",
        "description": "Location name-based query"
    }
]

def test_query_analysis(query: str, expected_mode: str = None) -> Dict[str, Any]:
    """Test a single query analysis"""
    
    request_data = {
        "query": query,
        "messages": [],
        "context_files": []
    }
    
    try:
        print(f"\n🔍 Testing: '{query}'")
        print(f"Expected mode: {expected_mode or 'Unknown'}")
        
        start_time = time.time()
        response = requests.post(
            QUERY_ANALYZE_ENDPOINT,
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        end_time = time.time()
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Analysis successful ({end_time - start_time:.2f}s)")
            print(f"   Recommended mode: {result['recommended_mode']}")
            print(f"   Confidence: {result['confidence']:.2f}")
            print(f"   Reasoning: {result['reasoning']}")
            
            if result.get('extracted_data'):
                print(f"   Extracted data: {result['extracted_data']}")
            
            # Check if recommendation matches expectation
            if expected_mode and result['recommended_mode'] == expected_mode:
                print(f"   ✅ Mode recommendation matches expectation")
            elif expected_mode:
                print(f"   ⚠️  Mode recommendation differs from expectation")
            
            return {
                "success": True,
                "result": result,
                "response_time": end_time - start_time,
                "matches_expected": result['recommended_mode'] == expected_mode if expected_mode else None
            }
        else:
            print(f"❌ Analysis failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return {
                "success": False,
                "error": f"HTTP {response.status_code}: {response.text}",
                "response_time": end_time - start_time
            }
            
    except requests.exceptions.Timeout:
        print(f"❌ Request timeout")
        return {"success": False, "error": "Timeout"}
    except requests.exceptions.RequestException as e:
        print(f"❌ Request error: {e}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return {"success": False, "error": str(e)}

def run_all_tests():
    """Run all test queries and generate a report"""
    
    print("🚀 Starting Intelligent Query Routing Tests")
    print("=" * 60)
    
    results = []
    total_tests = len(TEST_QUERIES)
    successful_tests = 0
    matching_tests = 0
    total_response_time = 0
    
    for i, test_case in enumerate(TEST_QUERIES, 1):
        print(f"\n📝 Test {i}/{total_tests}: {test_case['description']}")
        
        result = test_query_analysis(
            test_case["query"],
            test_case["expected_mode"]
        )
        
        results.append({
            "test_case": test_case,
            "result": result
        })
        
        if result["success"]:
            successful_tests += 1
            total_response_time += result["response_time"]
            
            if result.get("matches_expected"):
                matching_tests += 1
    
    # Generate summary report
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY REPORT")
    print("=" * 60)
    
    print(f"Total Tests: {total_tests}")
    print(f"Successful: {successful_tests} ({successful_tests/total_tests*100:.1f}%)")
    print(f"Mode Accuracy: {matching_tests} ({matching_tests/total_tests*100:.1f}%)")
    
    if successful_tests > 0:
        avg_response_time = total_response_time / successful_tests
        print(f"Average Response Time: {avg_response_time:.2f}s")
    
    # Detailed results
    print("\n📋 DETAILED RESULTS:")
    for i, test_result in enumerate(results, 1):
        test_case = test_result["test_case"]
        result = test_result["result"]
        
        status = "✅" if result["success"] else "❌"
        accuracy = ""
        if result["success"] and result.get("matches_expected") is not None:
            accuracy = "✅" if result["matches_expected"] else "⚠️"
        
        print(f"{i:2d}. {status} {accuracy} {test_case['description']}")
        if result["success"]:
            rec_mode = result["result"]["recommended_mode"]
            confidence = result["result"]["confidence"]
            print(f"    → {rec_mode} (confidence: {confidence:.2f})")
        else:
            print(f"    → Error: {result['error']}")

def test_single_query():
    """Interactive mode for testing individual queries"""
    
    print("\n🔍 Interactive Query Testing")
    print("Enter queries to test (or 'quit' to exit):")
    
    while True:
        query = input("\nQuery: ").strip()
        
        if query.lower() in ['quit', 'exit', 'q']:
            break
        
        if not query:
            continue
        
        test_query_analysis(query)

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        test_single_query()
    else:
        run_all_tests()
        
        # Ask if user wants interactive mode
        choice = input("\n🤔 Would you like to test individual queries? (y/N): ").strip().lower()
        if choice in ['y', 'yes']:
            test_single_query()
