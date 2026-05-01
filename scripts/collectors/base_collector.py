"""Base Collector - Abstract base class for all data collectors"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional, Tuple
import logging
import httpx

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """Abstract base class for data collectors"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the collector

        Args:
            api_key: API key for the service (if required)
        """
        self.api_key = api_key
        self.session: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry"""
        # SSL 인증서 검증 비활성화 (기상청 API 허브 호환성)
        self.session = httpx.AsyncClient(timeout=30.0, verify=False)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.aclose()

    @abstractmethod
    async def collect(
        self,
        region_code: str,
        date_range: Optional[Tuple[datetime, datetime]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Collect data for a specific region and date range

        Args:
            region_code: Region code (읍면동 코드)
            date_range: Tuple of (start_date, end_date)
            **kwargs: Additional parameters

        Returns:
            Dictionary containing collected data

        Raises:
            CollectorError: If data collection fails
        """
        pass

    async def _make_request(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        method: str = "GET"
    ) -> Dict[str, Any]:
        """
        Make HTTP request with error handling

        Args:
            url: Request URL
            params: Query parameters
            method: HTTP method (GET/POST)

        Returns:
            Response data as dictionary

        Raises:
            httpx.HTTPError: If request fails
        """
        if not self.session:
            raise RuntimeError("Session not initialized. Use async context manager.")

        try:
            if method.upper() == "GET":
                response = await self.session.get(url, params=params)
            elif method.upper() == "POST":
                response = await self.session.post(url, json=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error {e.response.status_code}: {url}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error: {url} - {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error: {url} - {str(e)}")
            raise


class CollectorError(Exception):
    """Base exception for collector errors"""
    pass
