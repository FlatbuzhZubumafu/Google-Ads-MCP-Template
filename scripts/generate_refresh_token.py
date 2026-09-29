#!/usr/bin/env python
"""Generates a Google Ads API refresh token for local (stdio) use.

Run this once on your own machine after creating an OAuth client in
Google Cloud Console:

    python scripts/generate_refresh_token.py \
        --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET

A browser window opens for Google sign-in; approve the Google Ads scope
and the refresh token is printed. Put it in GOOGLE_ADS_REFRESH_TOKEN
(see .env.example). Requires http://localhost:8085/ to be listed as an
authorized redirect URI on the OAuth client, or use a "Desktop app"
client, which allows localhost redirects automatically.

Note: while the OAuth consent screen is in "Testing" publishing status,
Google expires refresh tokens after 7 days — publish the app to
production for a long-lived token.
"""

import argparse
import os

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/adwords"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--client-id",
        default=os.environ.get("GOOGLE_ADS_OAUTH_CLIENT_ID"),
        help="OAuth client ID (or set GOOGLE_ADS_OAUTH_CLIENT_ID)",
    )
    parser.add_argument(
        "--client-secret",
        default=os.environ.get("GOOGLE_ADS_OAUTH_CLIENT_SECRET"),
        help="OAuth client secret (or set GOOGLE_ADS_OAUTH_CLIENT_SECRET)",
    )
    parser.add_argument("--port", type=int, default=8085)
    args = parser.parse_args()

    if not (args.client_id and args.client_secret):
        parser.error("--client-id and --client-secret are required")

    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": args.client_id,
                "client_secret": args.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
    )
    # access_type=offline + consent prompt are required to get a refresh
    # token on repeat authorizations, not just the first one.
    credentials = flow.run_local_server(
        port=args.port, access_type="offline", prompt="consent"
    )

    print("\nAdd these to your environment (.env):\n")
    print(f"GOOGLE_ADS_OAUTH_CLIENT_ID={args.client_id}")
    print(f"GOOGLE_ADS_OAUTH_CLIENT_SECRET={args.client_secret}")
    print(f"GOOGLE_ADS_REFRESH_TOKEN={credentials.refresh_token}")


if __name__ == "__main__":
    main()
