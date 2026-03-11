# AzerBot v2 Implementation Plan

## Vision
Card-driven Azeroth RP engine using curated local libraries and bindings, modeled after The Continent Bot.

## Architecture
- azerbot/: main.py, config.py, response_engine.py, scene_memory.py, card_loader.py, bindings.py, guardrails.py, validators.py
- data/: bindings.json, characters/, places/, creatures/
- schemas/: character.schema.json, place.schema.json, creature.schema.json
- tests/: test_card_loader.py, test_bindings.py, test_scene_memory.py, test_validators.py, test_response_engine.py

## Core Layers
- Character Cards
- Place Cards
- Creature Cards
- Channel Bindings
- Scene Memory
- Response Orchestration

## Deprecations
- OC submission/approval/rejection workflows
- Themed distortion replaced by neutral safety fallback

## Immediate Tasks Completed
- Scaffolds for loaders, bindings, schemas, memory, response assembly
- Neutral fallback configured

## Next Steps
- Populate capital city place cards and key character cards
- Implement selection of active character and orchestration rules
