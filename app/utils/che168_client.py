"""CHE168 API client."""

import requests
from typing import Dict, Any, Optional, List
from datetime import date
from urllib.parse import urlencode

from app.utils.config import config, env_config
from app.utils.logger import logger
from app.utils.retry import retry_sync


class CHE168Client:
    """Client for CHE168.COM API."""
    
    def __init__(self):
        """Initialize CHE168 API client."""
        self.api_key = env_config.get_che168_api_key()
        self.access_name = env_config.get_che168_access_name()
        che168_config = config.get_che168_config()
        self.base_url = che168_config.get('base_url', '').format(access_name=self.access_name)
        self.endpoints = che168_config.get('endpoints', {})
        self.timeout = config.get_api_config().get('timeout_seconds', 30)
        
        if not self.api_key:
            raise ValueError("CHE168_API_KEY is not set in environment variables")
        if not self.access_name:
            raise ValueError("CHE168_ACCESS_NAME is not set in environment variables")
    
    def _build_url(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> str:
        """
        Build full URL for API request.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            Full URL string
        """
        url = f"{self.base_url}{endpoint}"
        
        # Add API key to params
        if params is None:
            params = {}
        params['api_key'] = self.api_key
        
        # Build query string
        query_string = urlencode(params, doseq=True)
        return f"{url}?{query_string}"
    
    def _make_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Make HTTP request to API with retry mechanism.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            JSON response as dictionary
            
        Raises:
            requests.RequestException: If request fails after all retries
        """
        url = self._build_url(endpoint, params)
        
        def _request():
            # Each request creates a fresh connection (no keep-alive/pooling)
            # This avoids ConnectionResetError when server closes idle connections
            response = requests.get(
                url,
                timeout=self.timeout,
                headers={
                    'User-Agent': 'CHE168-Parser/1.0',
                    'Accept': 'application/json',
                    'Connection': 'close',  # Force close connection after each request
                },
            )
            response.raise_for_status()
            return response.json()
        
        try:
            return retry_sync(_request)
        except Exception as e:
            logger.error(f"API request failed for {endpoint}: {e}")
            raise
    
    def get_filters(self) -> Dict[str, Any]:
        """
        Get available filter values.
        
        Returns:
            Dictionary with filter values (mark, model, transmission_type, etc.)
        """
        logger.debug("Fetching filters from CHE168 API")
        endpoint = self.endpoints.get('filters', '/filters')
        return self._make_request(endpoint)
    
    def get_offers(
        self,
        page: int,
        mark: Optional[str] = None,
        model: Optional[str] = None,
        transmission_type: Optional[str] = None,
        color: Optional[str] = None,
        body_type: Optional[str] = None,
        engine_type: Optional[str] = None,
        year_from: Optional[int] = None,
        year_to: Optional[int] = None,
        km_age_from: Optional[int] = None,
        km_age_to: Optional[int] = None,
        price_from: Optional[float] = None,
        price_to: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Get list of offers with pagination and filters.
        
        Args:
            page: Page number (required)
            mark: Car brand
            model: Car model
            transmission_type: Transmission type
            color: Color
            body_type: Body type
            engine_type: Engine type
            year_from: Minimum year
            year_to: Maximum year
            km_age_from: Minimum mileage (km)
            km_age_to: Maximum mileage (km)
            price_from: Minimum price (CNY)
            price_to: Maximum price (CNY)
            
        Returns:
            Dictionary with 'result' (list of offers) and 'meta' (pagination info)
        """
        params = {'page': page}
        
        # Add optional filters
        if mark:
            params['mark'] = mark
        if model:
            params['model'] = model
        if transmission_type:
            params['transmission_type'] = transmission_type
        if color:
            params['color'] = color
        if body_type:
            params['body_type'] = body_type
        if engine_type:
            params['engine_type'] = engine_type
        if year_from:
            params['year_from'] = year_from
        if year_to:
            params['year_to'] = year_to
        if km_age_from:
            params['km_age_from'] = km_age_from
        if km_age_to:
            params['km_age_to'] = km_age_to
        if price_from:
            params['price_from'] = price_from
        if price_to:
            params['price_to'] = price_to
        
        endpoint = self.endpoints.get('offers', '/offers')
        return self._make_request(endpoint, params)
    
    def get_change_id(self, date_param: date) -> int:
        """
        Get initial change_id for a specific date.
        
        Args:
            date_param: Date to get change_id for (YYYY-MM-DD format)
            
        Returns:
            Change ID (integer)
        """
        date_str = date_param.strftime('%Y-%m-%d')
        params = {'date': date_str}
        
        logger.debug(f"Fetching change_id for date {date_str} from CHE168 API")
        endpoint = self.endpoints.get('change_id', '/change_id')
        response = self._make_request(endpoint, params)
        
        # Response format: {"change_id": 123456789}
        return response.get('change_id')
    
    def get_changes(self, change_id: int) -> Dict[str, Any]:
        """
        Get changes starting from specified change_id.
        
        Args:
            change_id: Starting change ID
            
        Returns:
            Dictionary with 'result' (list of changes) and 'meta' (pagination info with next_change_id)
        """
        params = {'change_id': change_id}
        
        logger.debug(f"Fetching changes from change_id {change_id} from CHE168 API")
        endpoint = self.endpoints.get('changes', '/changes')
        return self._make_request(endpoint, params)
    
    def get_offer(self, inner_id: str) -> Dict[str, Any]:
        """
        Get details of specific offer by inner_id.
        
        Args:
            inner_id: Inner ID of the offer
            
        Returns:
            Dictionary with offer details
        """
        params = {'inner_id': inner_id}
        
        logger.debug(f"Fetching offer {inner_id} from CHE168 API")
        endpoint = self.endpoints.get('offer', '/offer')
        return self._make_request(endpoint, params)
