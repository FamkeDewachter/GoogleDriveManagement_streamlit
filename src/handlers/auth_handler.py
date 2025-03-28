from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive.readonly",
]


class AuthHandler:
    def __init__(self, client_config, redirect_uri):
        self.client_config = client_config
        self.redirect_uri = redirect_uri
        self.flow = None

    def initialize_flow(self):
        self.flow = Flow.from_client_config(
            client_config=self.client_config,
            scopes=SCOPES,
            redirect_uri=self.redirect_uri,
        )
        return self.flow

    def fetch_token(self, code):
        if not self.flow:
            self.initialize_flow()
        return self.flow.fetch_token(code=code)

    def get_credentials(self):
        return self.flow.credentials if self.flow else None

    def get_auth_url(self):
        if not self.flow:
            self.initialize_flow()
        return self.flow.authorization_url(
            prompt="consent",
            access_type="offline",
            include_granted_scopes="false",
        )[0]

    def get_user_info(self, creds):
        people_service = build("people", "v1", credentials=creds)
        profile = (
            people_service.people()
            .get(resourceName="people/me", personFields="names,emailAddresses")
            .execute()
        )
        return {
            "name": profile.get("names", [{}])[0].get(
                "displayName", "Unknown"
            ),
            "email": profile.get("emailAddresses", [{}])[0].get(
                "value", "unknown"
            ),
        }

    def build_drive_service(self, creds):
        return build("drive", "v3", credentials=creds, static_discovery=False)
