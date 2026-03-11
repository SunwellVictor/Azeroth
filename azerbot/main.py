import os
import sys
import json
import logging
import random
import asyncio
import datetime
import re
import httpx
import time
import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Dict, List

# Local Imports
from logger import setup_logger
from utils import (
    get_config,
    get_fallback_message,
    check_guardrails,
    log_audit_event,
    get_model_chain,
    load_usage_state,
    save_usage_state,
    BASE_DIR
)
from scene_syntax import parse_trailing_directives
from scene_memory import get_state, update_state
from response_engine import build_messages
from card_loader import resolve_creature

# Load Environment Variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Setup Logging
logger = setup_logger()

# Load Configuration
CONFIG = get_config()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
GUILD_ID = os.getenv("GUILD_ID")

if not DISCORD_TOKEN or not OPENROUTER_API_KEY:
    logger.critical("Missing DISCORD_TOKEN or OPENROUTER_API_KEY in .env")
    # sys.exit(1) # Commented out to allow partial run if user wants to test logic without tokens

# Bot Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# --- Cost Control State ---
# In-memory daily counter (still useful for speed, but monthly needs persistence)
daily_usage_counter = 0
last_reset_date = datetime.date.today()
user_cooldowns: Dict[int, float] = {}

def check_cost_control(user_id: int) -> tuple[bool, str]:
    global daily_usage_counter, last_reset_date
    
    # 1. Daily Reset & Cap (In-Memory)
    today = datetime.date.today()
    if today > last_reset_date:
        daily_usage_counter = 0
        last_reset_date = today
    
    if daily_usage_counter >= CONFIG.get("daily_cap", 300):
        return False, "AzerBot is at daily capacity. Try again tomorrow."

    # 2. Monthly Cap (Persistent)
    state = load_usage_state()
    current_month = today.month
    
    # Reset if month changed
    if state.get("last_reset_month") != current_month:
        state["monthly_count"] = 0
        state["last_reset_month"] = current_month
        save_usage_state(state)
        
    if state["monthly_count"] >= CONFIG.get("monthly_cap", 1000):
        return False, "AzerBot is at monthly capacity. Try again next month."
        
    # 3. User Cooldown
    now = asyncio.get_running_loop().time()
    last_used = user_cooldowns.get(user_id, 0)
    cooldown = CONFIG.get("env_cooldown", 60)
    
    if now - last_used < cooldown:
        remaining = int(cooldown - (now - last_used))
        return False, f"Rate limited. Try again in {remaining}s."
        
    return True, ""

def update_cost_usage(user_id: int):
    global daily_usage_counter
    
    # Update Daily
    daily_usage_counter += 1
    
    # Update Monthly (Persistent)
    state = load_usage_state()
    today = datetime.date.today()
    
    # Handle month rollover just in case it happened between check and update
    if state.get("last_reset_month") != today.month:
        state["monthly_count"] = 0
        state["last_reset_month"] = today.month
        
    state["monthly_count"] += 1
    save_usage_state(state)
    
    # Update Cooldown
    user_cooldowns[user_id] = asyncio.get_running_loop().time()

# --- OpenRouter Logic ---

# Model Cooldown State
_model_cooldowns: Dict[str, float] = {}
MODEL_COOLDOWN_SEC = 300

def _get_eligible_models() -> List[str]:
    """Returns models that are not on cooldown."""
    chain = get_model_chain()
    now = time.monotonic()
    eligible = [m for m in chain if _model_cooldowns.get(m, 0.0) <= now]
    
    # If all models are on cooldown, reset and try all (emergency release)
    if not eligible:
        _model_cooldowns.clear()
        return chain
    return eligible

def _cooldown_model(slug: str):
    """Puts a model on cooldown."""
    _model_cooldowns[slug] = time.monotonic() + MODEL_COOLDOWN_SEC

def _is_transient_error(status: int, text: str) -> bool:
    """Checks if an error is likely temporary (5xx, 429, 404-no-endpoints)."""
    if status in (502, 503, 504): return True
    if status == 429: return True
    if status == 404 and "No endpoints found" in text: return True
    return False

async def generate_rp_response(messages: List[Dict[str, str]]) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://github.com/YourRepo/AzerBot", # Placeholder
        "X-Title": "AzerBot"
    }

    max_tokens = 250
    temperature = CONFIG.get("temperature", 0.8)
    
    # --- Model Fallback Chain Loop ---
    candidates = _get_eligible_models()
    last_error = None
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for model_slug in candidates:
            payload = {
                "model": model_slug,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            
            try:
                response = await client.post(url, headers=headers, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    if 'choices' in data and len(data['choices']) > 0:
                        content = data['choices'][0]['message']['content']
                        return content.strip()
                    else:
                        logger.error(f"Empty choices from {model_slug}: {data}")
                        _cooldown_model(model_slug)
                        continue # Try next model
                        
                # Handle Non-200
                logger.warning(f"Model {model_slug} failed: {response.status_code} - {response.text}")
                
                if _is_transient_error(response.status_code, response.text):
                    _cooldown_model(model_slug)
                    continue # Try next model
                else:
                    # Permanent error (e.g. 401 Auth), break chain
                    last_error = f"Permanent Error: {response.status_code}"
                    break
                    
            except (httpx.RequestError, httpx.TimeoutException) as e:
                logger.warning(f"Network error with {model_slug}: {e}")
                _cooldown_model(model_slug)
                last_error = str(e)
                continue
    
    # If we reach here, all models failed
    logger.error(f"All models failed. Last error: {last_error}")
    return get_fallback_message()

# --- Bot Events ---
@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        if GUILD_ID:
            guild = discord.Object(id=GUILD_ID)
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
            logger.info(f"Synced {len(synced)} slash commands to guild {GUILD_ID}.")
        else:
            synced = await bot.tree.sync()
            logger.info(f"Synced {len(synced)} slash commands globally.")
    except Exception as e:
        logger.error(f"Failed to sync slash commands: {e}")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    content = message.content.strip()

    rp_text, directives, warnings = parse_trailing_directives(content)
    if warnings:
        logger.warning(f"Scene directive warnings: {warnings} (user={message.author.id}, channel={message.channel.id})")

    if not directives["env"] and not directives["place"] and not directives["char"] and not directives["creature"]:
        await bot.process_commands(message)
        return

    channel_id = message.channel.id
    state = get_state(channel_id)
    prev_place = str(state.get("active_place_id", "")).strip().lower()
    new_place = str(directives.get("place", "")).strip().lower()
    place_changed = bool(new_place) and new_place != prev_place

    update_state(
        channel_id,
        place_id=new_place,
        char_id=str(directives.get("char", "")).strip().lower(),
        creature_id=str(directives.get("creature", "")).strip().lower(),
        place_changed=place_changed
    )

    if not directives["env"]:
        return

    state = get_state(channel_id)
    active_place_id = str(state.get("active_place_id", "")).strip().lower()
    active_char_id = str(directives.get("char", "")).strip().lower() or str(state.get("active_char_id", "")).strip().lower()
    active_creature_id = str(directives.get("creature", "")).strip().lower() or str(state.get("active_creature_id", "")).strip().lower()
    creature_source = "explicit_tag" if str(directives.get("creature", "")).strip() else ("scene_memory" if str(state.get("active_creature_id", "")).strip() else "")
    if active_creature_id:
        resolved, resolved_id = resolve_creature(active_creature_id)
        if resolved_id:
            logger.info(f"Resolved creature '{active_creature_id}' -> '{resolved_id}' source={creature_source}")
        else:
            logger.warning(f"Unresolved creature '{active_creature_id}' source={creature_source}")

    if check_guardrails(rp_text):
        await message.reply(get_fallback_message())
        log_audit_event(message.author.id, message.channel.id, "!env", True, 0)
        return

    messages, err = build_messages(channel_id, rp_text, active_place_id, active_char_id, active_creature_id)
    if err:
        await message.reply(err)
        return

    allowed, reason = check_cost_control(message.author.id)
    if not allowed:
        await message.reply(reason, delete_after=10)
        return

    async with message.channel.typing():
        update_cost_usage(message.author.id)
        response = await generate_rp_response(messages)
        await message.reply(response)

        summary = response.strip()
        if len(summary) > 600:
            summary = summary[:600]
        update_state(channel_id, scene_summary=summary)

        estimated_tokens = (len(rp_text) + len(response)) // 4
        log_audit_event(message.author.id, message.channel.id, "!env", False, estimated_tokens)
    return


# --- Slash Commands (OC System) ---

@bot.tree.command(name="oc_submit", description="Submit an Original Character for approval.")
@app_commands.describe(
    name="Character Name",
    race="Race or Species",
    role="Class or Role",
    vibe_tags="Keywords (e.g., gloomy, noble)",
    short_bio="Brief backstory",
    appearance="Visual description",
    hooks="Roleplay hooks"
)
async def oc_submit(interaction: discord.Interaction, name: str, race: str, role: str, vibe_tags: str, short_bio: str, appearance: str, hooks: str):
    await interaction.response.send_message("This feature is deprecated. Character cards will be curated locally.", ephemeral=True)

@bot.tree.command(name="oc_approve", description="Approve a pending OC (Staff Only).")
async def oc_approve(interaction: discord.Interaction, oc_id: str):
    await interaction.response.send_message("This feature is deprecated. Character cards will be curated locally.", ephemeral=True)

@bot.tree.command(name="oc_reject", description="Reject a pending OC (Staff Only).")
async def oc_reject(interaction: discord.Interaction, oc_id: str, reason: str):
    await interaction.response.send_message("This feature is deprecated. Character cards will be curated locally.", ephemeral=True)

@bot.tree.command(name="oc_show", description="Display an OC card.")
async def oc_show(interaction: discord.Interaction, name_or_id: str):
    registry = load_oc_registry()
    target_oc = None

    # Try ID match
    if name_or_id in registry:
        target_oc = registry[name_or_id]
    else:
        # Try Name match (case-insensitive)
        for data in registry.values():
            if data['name'].lower() == name_or_id.lower():
                target_oc = data
                break
    
    if target_oc:
        embed = create_oc_embed(target_oc)
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"OC '{name_or_id}' not found.", ephemeral=True)

# Main Entry Point
if __name__ == "__main__":
    if not DISCORD_TOKEN:
        logger.error("No DISCORD_TOKEN found. Please configure .env file.")
    else:
        try:
            bot.run(DISCORD_TOKEN)
        except Exception as e:
            logger.critical(f"Bot crashed: {e}")
