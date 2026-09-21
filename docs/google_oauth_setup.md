# Google OAuth Setup (Gmail + Calendar) — Free Tier

1. Go to https://console.cloud.google.com/ and create a new project.
2. Enable APIs: **Gmail API** and **Google Calendar API**
   (APIs & Services -> Library -> search each -> Enable).
3. Configure the OAuth consent screen (APIs & Services -> OAuth consent screen):
   - User type: External (or Internal if you have a Workspace org)
   - Add your own Google account as a test user
   - Scopes: gmail.send, calendar.events
4. Create credentials: APIs & Services -> Credentials -> Create Credentials ->
   OAuth client ID -> Application type: **Desktop app**.
5. Download the JSON and save it as `credentials.json` in the project root
   (path is configurable via GOOGLE_CREDENTIALS_PATH in .env).
6. Leave `DRY_RUN=true` in `.env` while testing — tools will log what
   they *would* send instead of actually sending/creating anything.
7. The first real (non-dry-run) call will open a browser window for you
   to consent; a `token.json` will be saved afterward and reused.

All of this is within Google's free tier/quota for personal use.
