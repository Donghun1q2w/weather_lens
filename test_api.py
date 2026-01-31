"""Test script for PhotoSpot Korea API

Run this script to verify all endpoints are working correctly.

Usage:
    python test_api.py
"""
import asyncio
import httpx
from typing import Dict, Any

# API base URL
BASE_URL = "http://localhost:8000"
INTERNAL_API_KEY = "dev-internal-key"


class APITester:
    """API testing class"""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.results = []

    async def test_endpoint(
        self, method: str, path: str, description: str, **kwargs
    ) -> Dict[str, Any]:
        """Test a single endpoint"""
        url = f"{self.base_url}{path}"
        print(f"\n[TEST] {description}")
        print(f"  {method} {path}")

        try:
            async with httpx.AsyncClient() as client:
                if method == "GET":
                    response = await client.get(url, **kwargs)
                elif method == "POST":
                    response = await client.post(url, **kwargs)
                else:
                    raise ValueError(f"Unsupported method: {method}")

                status = response.status_code
                result = {
                    "description": description,
                    "method": method,
                    "path": path,
                    "status": status,
                    "success": 200 <= status < 300,
                }

                if result["success"]:
                    print(f"  ✓ Status: {status}")
                    try:
                        data = response.json()
                        print(f"  Response: {data}")
                    except:
                        print(f"  Response: {response.text[:200]}")
                else:
                    print(f"  ✗ Status: {status}")
                    print(f"  Error: {response.text}")

                self.results.append(result)
                return result

        except Exception as e:
            print(f"  ✗ Error: {e}")
            result = {
                "description": description,
                "method": method,
                "path": path,
                "status": 0,
                "success": False,
                "error": str(e),
            }
            self.results.append(result)
            return result

    async def run_all_tests(self):
        """Run all API tests"""
        print("=" * 60)
        print("PhotoSpot Korea API Test Suite")
        print("=" * 60)

        # Test root endpoint
        await self.test_endpoint("GET", "/", "Root endpoint")

        # Test health check
        await self.test_endpoint("GET", "/health", "Health check (UptimeRobot)")

        # Test themes
        await self.test_endpoint("GET", "/api/v1/themes", "Get all themes")
        await self.test_endpoint(
            "GET", "/api/v1/themes/1/top", "Get top regions for theme 1"
        )
        await self.test_endpoint(
            "GET",
            "/api/v1/themes/1/top?limit=5",
            "Get top 5 regions for theme 1",
        )

        # Test regions
        await self.test_endpoint(
            "GET", "/api/v1/regions/1168010100", "Get region detail"
        )
        await self.test_endpoint(
            "GET", "/api/v1/regions/1168010100/forecast", "Get region forecast"
        )

        # Test feedback
        feedback_data = {
            "region_code": "1168010100",
            "theme_id": 1,
            "score_success": True,
            "rating": 5,
            "comment": "Test feedback",
        }
        await self.test_endpoint(
            "POST",
            "/api/v1/feedback",
            "Submit feedback",
            json=feedback_data,
        )

        # Test map
        await self.test_endpoint(
            "GET", "/api/v1/map/boundaries", "Get map boundaries (default)"
        )
        await self.test_endpoint(
            "GET",
            "/api/v1/map/boundaries?level=sido&region_code=11",
            "Get map boundaries (filtered)",
        )

        # Test internal endpoints (authenticated)
        headers = {"X-API-Key": INTERNAL_API_KEY}

        await self.test_endpoint(
            "POST",
            "/internal/collect",
            "Trigger data collection (internal)",
            headers=headers,
        )
        await self.test_endpoint(
            "POST",
            "/internal/score",
            "Trigger score calculation (internal)",
            headers=headers,
        )
        await self.test_endpoint(
            "POST",
            "/internal/notify",
            "Trigger notification (internal)",
            headers=headers,
        )

        # Test internal endpoint without auth (should fail)
        await self.test_endpoint(
            "POST", "/internal/collect", "Trigger collection (no auth - should fail)"
        )

        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print test results summary"""
        print("\n" + "=" * 60)
        print("Test Results Summary")
        print("=" * 60)

        total = len(self.results)
        passed = sum(1 for r in self.results if r["success"])
        failed = total - passed

        print(f"Total tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success rate: {passed/total*100:.1f}%")

        if failed > 0:
            print("\nFailed tests:")
            for result in self.results:
                if not result["success"]:
                    print(f"  ✗ {result['description']}")
                    print(f"    {result['method']} {result['path']}")
                    if "error" in result:
                        print(f"    Error: {result['error']}")
                    else:
                        print(f"    Status: {result['status']}")


async def main():
    """Main test runner"""
    print("\nMake sure the API is running:")
    print("  python main.py")
    print("\nor")
    print("  uvicorn api.main:app --reload\n")

    tester = APITester(BASE_URL)
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())
