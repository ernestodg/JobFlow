#!/usr/bin/env python3
"""Test the analytics endpoint"""

import sys

import requests


def test_analytics_endpoint():
    """Test the follow-ups analytics endpoint"""
    try:
        # Test basic analytics endpoint
        print("Testing analytics endpoint...")
        response = requests.get("http://127.0.0.1:5001/api/followups/analytics", timeout=10)

        if response.status_code == 200:
            data = response.json()
            print("✅ Analytics endpoint working!")
            print(f"📊 Activity metrics: {data.get('activity_metrics', {}).get('total_followups', 0)} followups")
            print(f"📈 SLA violations: {data.get('sla_metrics', {}).get('total_violations', 0)}")
            print(f"💡 Generated insights: {len(data.get('insights', []))}")

            # Show insights
            insights = data.get("insights", [])
            if insights:
                print("\nGenerated insights:")
                for i, insight in enumerate(insights, 1):
                    print(f"  {i}. [{insight['type'].upper()}] {insight['message']}")
                    print(f"     → {insight['recommendation']}")

            # Show conversion rates
            conversion_rates = data.get("outcome_metrics", {}).get("conversion_rates", {})
            if conversion_rates:
                print("\nConversion rates by follow-up activity:")
                for bucket, metrics in conversion_rates.items():
                    print(
                        f"  {bucket}: {metrics['conversion_rate']:.1f}% ({metrics['positive_outcomes']}/{metrics['total_jobs']})"
                    )

            return True
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
            return False

    except requests.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    success = test_analytics_endpoint()
    sys.exit(0 if success else 1)
