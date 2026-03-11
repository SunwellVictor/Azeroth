# AzerBot Deployment Guide

## Part 1: Discord Bot Setup
1.  Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2.  Click **New Application** and name it (e.g., "AzerBot").
3.  Go to the **Bot** tab:
    *   Click **Reset Token** and copy the token. Save this for later (you will need it for `.env`).
    *   Scroll down to **Privileged Gateway Intents**.
    *   **Enable "Message Content Intent"**. (Critical for `!env` to work).
    *   Enable "Server Members Intent" (Optional, but good for future).
    *   Click **Save Changes**.
4.  Go to the **OAuth2** -> **URL Generator** tab:
    *   Select scopes: `bot` and `applications.commands`.
    *   Select permissions: `Send Messages`, `Read Message History`, `Embed Links`, `Attach Files`.
    *   Copy the generated URL and open it in your browser to invite the bot to your server.

## Part 2: Railway Deployment (Cloud Hosting)
1.  **Push your code to GitHub:**
    *   Create a new repository on GitHub.
    *   Push the `Azeroth` folder content to it.
2.  **Create a Railway Project:**
    *   Go to [Railway.app](https://railway.app/).
    *   Click **New Project** -> **Deploy from GitHub repo**.
    *   Select your repository.
3.  **Configure Variables:**
    *   Go to the **Variables** tab in your new service.
    *   Add the following:
        *   `DISCORD_TOKEN`: (The token you copied in Part 1)
        *   `OPENROUTER_API_KEY`: (Your OpenRouter key)
4.  **Configure Start Command:**
    *   Go to the **Settings** tab.
    *   Scroll down to **Start Command**.
    *   Enter: `python azerbot/main.py`
    *   (Railway will automatically install dependencies from `requirements.txt`).
5.  **Deploy:**
    *   Railway should automatically redeploy. Check the **Logs** tab to see "Logged in as AzerBot".

## Part 3: Setting Up Locations (Channels)
**How AzerBot v1 Works:**
For this version, the bot reads the **Discord Channel Name** directly to understand the location. You do **not** need to upload JSON files for locations yet.

**Recommended Setup:**
1.  Create Category: `--- AZEROTH ---`
2.  Create Channels with descriptive names:
    *   `#stormwind-market`
    *   `#orgrimmar-gates`
    *   `#stranglethorn-vale`
    *   `#dalaran-sewers`

**Usage:**
*   Go to `#stormwind-market`.
*   Type: `The crowd is bustling today. !env`
*   AzerBot will see the channel name "stormwind-market" and generate a description fitting that location.

---

## Appendix: Future-Proofing (JSON Templates)
If you plan to upgrade to a "Continent Bot" style system later (where channels map to detailed JSON data), you can use the template below. **Note: AzerBot v1 does not use this yet.**

**File:** `data/places/stormwind.json`
```json
{
  "id": "stormwind",
  "name": "Stormwind City",
  "description": "The capital city of the Kingdom of Stormwind and the largest human city on Azeroth.",
  "traits": ["bustling", "majestic", "stone", "alliance"],
  "npcs": ["Guard", "Merchant", "Noble"],
  "ambience": "The sound of marching boots and distant cathedral bells."
}
```
