# AzerBot v1 - Setup Guide

## Prerequisites
- Python 3.10+
- Discord Bot Token (with Message Content Intent)
- OpenRouter API Key

## Installation
1.  Navigate to `azerbot/`:
    ```bash
    cd azerbot
    ```
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Configure environment:
    ```bash
    cp .env.example .env
    # Edit .env with your tokens
    ```

## Usage
Run the bot:
```bash
python main.py
```

## Features
### !env - Environmental Narration
-   **Usage:** End your message with `!env`.
-   **Example:** "The market is busy today. !env"
-   **Guardrails:** Rejects canon names (e.g., Thrall, Jaina).
-   **Fail-safe:** If rejected or error, returns "Veil Distortion" text.

### OC System (Original Characters)
-   **Submit:** `/oc_submit` (Name, Race, Role, Vibe, Bio, Appearance, Hooks)
-   **Approve:** `/oc_approve <id>` (Staff only)
-   **Reject:** `/oc_reject <id> <reason>` (Staff only)
-   **Show:** `/oc_show <name_or_id>`
-   **Trigger:**
    -   `!oc Name` at the end of a message.
    -   `[[OC:Name]]` anywhere in a message.

## Configuration
-   `config.json`: Adjust caps, cooldowns, and prompts.
-   `guardrails.json`: Add blocked names or phrases.
-   `distortion.json`: Add custom error messages.
