import requests
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from web_system.models import TTLockToken


class TTLockAPIError(Exception):
    """Base exception for errors related to TTLock API"""

    pass


class TTLockAPI:
    """Service Class to interact with TTLock API"""

    BASE_URL = "https://euapi.ttlock.com/"

    def __init__(self):
        self.username = settings.TTLOCK_USERNAME
        self.password = settings.TTLOCK_PASSWORD
        self.client_id = settings.TTLOCK_CLIENT_ID
        self.client_secret = settings.TTLOCK_CLIENT_SECRET

    def _get_access_token(self):
        """Used by public methods of this class to retrieve the access token from the DB, refresh it if needed,
        or create it from stratch"""

        token = TTLockToken.objects.first()

        if not token:
            return self._create_access_token()

        now = timezone.now()
        # if the token expires in less than 1 day, refresh it
        if token.expires_in <= (now + timedelta(days=1)):
            return self._refresh_access_token(token)

        return token.access_token

    def _create_access_token(self):
        """Retrieve the access token from TTlock API and save it into DB"""

        data = {
            "clientSecret": self.client_secret,
            "username": self.username,
            "password": self.password,
        }
        response = self._request("oauth2/token", method="POST", data=data)

        expires_in = response["expires_in"]

        token = TTLockToken.objects.create(
            access_token=response["access_token"],
            refresh_token=response["refresh_token"],
            expires_in=timezone.now() + timedelta(seconds=expires_in),
        )

        return token.access_token

    def _refresh_access_token(self, token):
        """Use refresh_token to obtain a new access_token"""

        data = {
            "clientSecret": self.client_secret,
            "grantType": "refresh_token",
            "refresh_token": token.refresh_token,
        }
        response = self._request("oauth2/token", method="POST", data=data)

        expires_in = response["expires_in"]

        token.access_token = response["access_token"]
        token.refresh_token = response["refresh_token"]
        token.expires_in = timezone.now() + timedelta(seconds=expires_in)
        token.save()

        return token.access_token

    def _request(self, endpoint, method="GET", params=None, data=None):
        """Used by public methods of this class to make HTTP requests to TTLock API endpoints"""

        url = f"{self.BASE_URL}/{endpoint}"

        if method == "GET":
            params.update({"clientId": self.client_id})
        elif method == "POST":
            data.update({"clientId": self.client_id})

        try:
            response = requests.request(
                method, url, params=params, data=data, timeout=10
            )
            response.raise_for_status()

            # Check if API response contains error code
            response_data = response.json()
            if "errcode" in response_data and response_data["errcode"] != 0:
                raise TTLockAPIError(f"TTLock API error: {response_data.get("errmsg")}")

            return response_data

        except requests.RequestException as e:
            # Catch timeout, connection errors, 4xx, 5xx
            raise TTLockAPIError(f"Communication error with TTLock server: {str(e)}")

    def get_lock_list(self):
        """Method used to fetch all the locks from TTLock"""

        date = int(timezone.now().timestamp() * 1000)
        access_token = self._get_access_token()

        return self._request(
            "v3/lock/list",
            params={
                "accessToken": access_token,
                "pageNo": 1,
                "pageSize": 20,
                "date": date,
            },
        )
