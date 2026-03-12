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
from typing import Optional, Dict, List, Any

# Local Imports
from logger import setup_logger
from utils import (
    get_config,
    get_fallback_message,
    check_guardrails,
    log_audit_event,
    log_audit_event_ex,
    get_model_chain,
    load_usage_state,
    save_usage_state,
    BASE_DIR,
    split_for_discord,
    log_error_event,
    log_debug_event,
    is_strict_third_person,
    third_person_violations
)
from scene_syntax import parse_trailing_directives
from scene_memory import get_state, update_state, clear_state
from response_engine import build_messages, repair_incomplete_response
from card_loader import resolve_creature, resolve_player_character
from validators import validate_rp_tag_configuration

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
    try:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://github.com/YourRepo/AzerBot",
            "X-Title": "AzerBot"
        }

        max_tokens = 280
        temperature = CONFIG.get("temperature", 0.8)

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
                        logger.error(f"Empty choices from {model_slug}: {data}")
                        _cooldown_model(model_slug)
                        continue

                    logger.warning(f"Model {model_slug} failed: {response.status_code} - {response.text}")

                    if _is_transient_error(response.status_code, response.text):
                        _cooldown_model(model_slug)
                        continue
                    last_error = f"Permanent Error: {response.status_code}"
                    break

                except (httpx.RequestError, httpx.TimeoutException) as e:
                    logger.warning(f"Network error with {model_slug}: {e}")
                    _cooldown_model(model_slug)
                    last_error = str(e)
                    continue

        logger.error(f"All models failed. Last error: {last_error}")
        return ""
    except Exception as e:
        logger.exception(f"OpenRouter generation failed: {e}")
        return ""

def _env_failure_text() -> str:
    return random.choice([
        "AzerBot falters for a moment and does not answer.",
        "AzerBot loses the thread of the scene.",
        "AzerBot cannot complete that reply right now."
    ])

async def _send_chunks(message: discord.Message, chunks: List[str]) -> bool:
    if not chunks:
        return True
    try:
        await message.reply(chunks[0])
        for chunk in chunks[1:]:
            await message.channel.send(chunk)
        return True
    except Exception as e:
        logger.exception(f"Discord send failed: {e}")
        return False

def _make_neutral_scene_summary(place_id: str, creature_id: str, response: str) -> str:
    place = (place_id or "").strip()
    creature = (creature_id or "").strip()
    text = (response or "").lower()

    mood = "steady"
    if any(w in text for w in ["tension", "tense", "tightens", "unease", "uneasy", "watchful", "wary", "dread"]):
        mood = "tense"
    elif any(w in text for w in ["calm", "quiet", "still", "gentle"]):
        mood = "calm"

    if place and creature:
        s = f"Scene remains in {place} with {mood} mood and possible {creature} presence."
    elif place:
        s = f"Scene remains in {place} with {mood} mood."
    else:
        s = f"Scene continues with {mood} mood."

    if len(s) > 300:
        s = s[:300]
    return s

async def _handle_env(message: discord.Message, rp_text: str, directives: Dict[str, Any]) -> None:
    channel_id = message.channel.id
    user_id = message.author.id

    parsed_place_id = str(directives.get("place", "")).strip().lower()
    parsed_char_id = str(directives.get("char", "")).strip().lower()
    parsed_creature_id = str(directives.get("creature", "")).strip().lower()

    try:
        if check_guardrails(rp_text):
            await message.reply(get_fallback_message())
            log_audit_event(user_id, channel_id, "!env", True, 0)
            return

        state = get_state(channel_id)
        prev_place = str(state.get("active_place_id", "")).strip().lower()
        place_changed = bool(parsed_place_id) and parsed_place_id != prev_place
        update_state(channel_id, place_id=parsed_place_id, place_changed=place_changed)

        state = get_state(channel_id)
        active_place_id = str(state.get("active_place_id", "")).strip().lower()
        active_char_id = parsed_char_id
        active_creature_id = parsed_creature_id
        creature_source = "explicit_tag" if active_creature_id else "none"
        bound_player_id = resolve_player_character(str(user_id)) or ""
        if active_creature_id:
            resolved, resolved_id = resolve_creature(active_creature_id)
            if resolved_id:
                logger.info(f"Resolved creature '{active_creature_id}' -> '{resolved_id}' source={creature_source}")
            else:
                logger.warning(f"Unresolved creature '{active_creature_id}' source={creature_source}")

        messages, err = build_messages(channel_id, rp_text, active_place_id, active_char_id, active_creature_id, user_id=str(user_id))
        if err:
            await message.reply("AzerBot cannot complete that reply right now.")
            log_audit_event(user_id, channel_id, "!env", False, 0)
            return

        allowed, reason = check_cost_control(user_id)
        if not allowed:
            await message.reply(reason, delete_after=10)
            return

        async with message.channel.typing():
            update_cost_usage(user_id)
            response = await generate_rp_response(messages)
            if not response:
                await message.reply(_env_failure_text())
                return

            response = repair_incomplete_response(response)

            if not is_strict_third_person(response):
                repair_prompt = (
                    "Rewrite the following reply in strict third-person narration.\n"
                    "Rules: no first person, no second person, no direct player address (you/your) outside quoted dialogue.\n"
                    "Keep the same scene content, tone, and constraints.\n\n"
                    "TEXT TO REWRITE:\n"
                    f"{response}"
                )
                repaired = await generate_rp_response(messages + [{"role": "user", "content": repair_prompt}])
                if repaired and is_strict_third_person(repaired):
                    response = repaired
                else:
                    logger.warning(f"Third-person validation failed: {third_person_violations(response)}")
                    await message.reply(_env_failure_text())
                    return

            chunks = split_for_discord(response, 1900)
            response_len = len(response)
            split_occurred = len(chunks) > 1
            ok = await _send_chunks(message, chunks)
            if not ok:
                log_error_event(user_id, channel_id, directives, "discord_send", Exception("discord_send_failed"))
                return

            summary_to_store = _make_neutral_scene_summary(active_place_id, active_creature_id, response)
            scene_summary_strategy = "neutral_summary"
            update_state(channel_id, scene_summary=summary_to_store)
            scene_summary_written = True

            final_scene_summary_preview = summary_to_store[:120]

            log_debug_event({
                "event_type": "env_debug",
                "user_id": user_id,
                "channel_id": channel_id,
                "parsed_place_id": parsed_place_id,
                "parsed_char_id": parsed_char_id,
                "parsed_creature_id": parsed_creature_id,
                "place_changed": place_changed,
                "scene_summary_written": scene_summary_written,
                "scene_summary_strategy": scene_summary_strategy,
                "final_scene_summary_preview": final_scene_summary_preview,
                "final_char_used": active_char_id,
                "final_creature_used": active_creature_id,
                "remembered_place_id": prev_place,
                "final_place_id": active_place_id,
                "creature_source": creature_source,
                "response_length": response_len,
                "split_occurred": split_occurred
            })

            estimated_tokens = (len(rp_text) + len(response)) // 4
            log_audit_event(user_id, channel_id, "!env", False, estimated_tokens)
            log_audit_event_ex(user_id, channel_id, "!env_tags", {
                "place_id": active_place_id,
                "char_id": active_char_id,
                "creature_id": active_creature_id,
                "player_character_id": bound_player_id
            })
        return

    except Exception as e:
        logger.exception(f"!env failure: {e} user={user_id} channel={channel_id} directives={directives}")
        log_error_event(user_id, channel_id, directives, "env_handler", e)
        try:
            await message.reply(_env_failure_text())
        except Exception as e2:
            logger.exception(f"Discord send failed while reporting failure: {e2}")
        return

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

    if content == "!scene_end":
        channel_id = message.channel.id
        is_mod = False
        try:
            is_mod = bool(getattr(message.author, "guild_permissions", None) and message.author.guild_permissions.manage_messages)
        except Exception:
            is_mod = False

        if not is_mod:
            await message.reply("Only moderators may end the active scene.")
            return

        state = get_state(channel_id)
        place_id = str(state.get("active_place_id", "")).strip().lower()
        clear_state(channel_id)
        await message.reply("Scene cleared. AzerBot awaits the next scene.")
        log_audit_event_ex(message.author.id, channel_id, "!scene_end", {"place_id": place_id})
        return

    if content == "!scene_status":
        channel_id = message.channel.id
        scene = get_state(channel_id)
        place_id = str(scene.get("active_place_id", "")).strip() or "None"
        summary_present = "Yes" if str(scene.get("scene_summary", "")).strip() else "No"
        last_update = str(scene.get("last_updated", "")).strip() or "None"
        payload = f"Scene Status\nPlace: {place_id}\nSummary present: {summary_present}\nLast update: {last_update}"
        await message.reply(payload)
        log_audit_event_ex(message.author.id, channel_id, "!scene_status", {"place_id": place_id, "summary_present": summary_present == "Yes", "last_update": last_update})
        return

    rp_text, directives, warnings = parse_trailing_directives(content)
    if warnings:
        logger.warning(f"Scene directive warnings: {warnings} (user={message.author.id}, channel={message.channel.id})")

    try:
        ok, normalized = validate_rp_tag_configuration(directives, warnings)
    except Exception:
        ok, normalized = False, directives
    if not ok:
        await message.reply("Invalid RP tag configuration. Check syntax.")
        return
    directives = normalized

    if not directives["env"] and not directives["place"] and not directives["char"] and not directives["creature"]:
        await bot.process_commands(message)
        return

    if not directives["env"]:
        channel_id = message.channel.id
        state = get_state(channel_id)
        prev_place = str(state.get("active_place_id", "")).strip().lower()
        new_place = str(directives.get("place", "")).strip().lower()
        place_changed = bool(new_place) and new_place != prev_place
        update_state(channel_id, place_id=new_place, place_changed=place_changed)
        return

    await _handle_env(message, rp_text, directives)
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
