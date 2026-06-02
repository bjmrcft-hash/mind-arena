# Phase 1 Task: MindArena Engine Core + CLI

Build the complete Python engine package for MindArena, a multi-LLM debate system. The project root is this directory (`mind-arena/`).

## Architecture

Three-layer decoupled architecture:
- `engine/` — Independent Python package (CLI-runnable, no server dependency)
- `server/` — FastAPI web service (imports engine)
- `web/` — React frontend

Phase 1 focuses ONLY on `engine/`. Do NOT create server/ or web/ code.

## Engine Directory Structure

```
engine/
├── pyproject.toml              # Package config with dependencies
├── engine/
│   ├── __init__.py
│   ├── debate_engine.py        # Main debate engine class
│   ├── state_machine.py        # Formal FSM (16 state transitions)
│   ├── round_controller.py     # Round/exchange control
│   ├── context_manager.py      # Context building + rolling summary compression
│   ├── cold_start_detector.py  # 3-dimension cold start detection
│   ├── deviation_detector.py   # Topic deviation detector
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py       # Agent base class
│   │   ├── moderator_a.py      # Host A
│   │   ├── debater_b.py        # Debater B (pro)
│   │   └── debater_c.py        # Debater C (con)
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── llm_service.py      # Unified LLM wrapper (streaming + non-streaming)
│   │   └── model_router.py     # Heterogeneous model routing
│   ├── tts/
│   │   ├── __init__.py
│   │   └── tts_service.py      # TTS wrapper (edge-tts / OpenAI TTS)
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic data models
│   └── prompts/
│       ├── moderator.md        # A's prompt
│       ├── debater_b.md        # B's prompt
│       └── debater_c.md        # C's prompt
├── cli.py                      # CLI entry point
└── tests/
    ├── __init__.py
    ├── test_state_machine.py
    ├── test_engine.py
    └── test_cold_start.py
```

## Data Models (engine/models/schemas.py)

```python
from pydantic import BaseModel, Field
from uuid import uuid4
from datetime import datetime
from typing import Literal

class DebateConfig(BaseModel):
    max_rounds: int = 5
    max_exchanges_per_round: int = 10
    cold_start_threshold: int = 2
    message_min_length: int = 100
    message_max_length: int = 800
    similarity_threshold: float = 0.85
    auto_play_audio: bool = True
    streaming_output: bool = True
    mode: Literal["quick", "standard", "deep"] = "standard"
    models: dict[str, str] = Field(default_factory=lambda: {
        "A": "deepseek-r1",
        "B": "kimi-k2",
        "C": "qwen3.5-plus"
    })

class DebateSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    topic: str
    status: Literal["idle","running","paused","completed","stopped","error"] = "idle"
    current_round: int = 0
    current_exchange: int = 0
    config: DebateConfig = DebateConfig()
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None

class DebateRound(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    round_number: int
    dimension: str | None = None
    status: Literal["active","completed"] = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    session_id: str
    round_id: str
    role: Literal["A","B","C"]
    round_number: int
    exchange_number: int = 0
    content: str
    audio_url: str | None = None
    message_type: Literal[
        "topic_intro", "opening", "argument", "rebuttal",
        "summary", "level_up", "verdict"
    ]
    token_count: int | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

## State Machine (engine/state_machine.py)

Formal FSM with these states:
- IDLE, TOPIC_INTRO, OPENING, EXCHANGING, SUMMARIZING, LEVEL_UP, FINAL, COMPLETED
- PAUSED, STOPPED, ERROR

State transitions:
| Current | Event | Action | Target |
|---------|-------|--------|--------|
| IDLE | START | Create session, A decompose topic | TOPIC_INTRO |
| TOPIC_INTRO | A_DONE | Broadcast A intro, assign B/C stances | OPENING |
| OPENING | BC_OPENED | B/C each complete 1 opening statement | EXCHANGING |
| EXCHANGING | EXCHANGE_LIMIT | Exchange count reaches limit | SUMMARIZING |
| EXCHANGING | COLD_START | Cold start detection triggered | SUMMARIZING |
| EXCHANGING | USER_SKIP | User skips round | SUMMARIZING |
| SUMMARIZING | A_SUMMARIZED | A completes round summary | LEVEL_UP |
| LEVEL_UP | ROUND_REMAIN | round < max_rounds | EXCHANGING |
| LEVEL_UP | ROUND_EXHAUST | round == max_rounds | FINAL |
| FINAL | A_VERDICT | A completes final summary | COMPLETED |
| *any* | USER_PAUSE | Pause engine | PAUSED |
| PAUSED | USER_RESUME | Resume engine | back to original |
| *any* | USER_STOP | Stop debate | STOPPED |
| *any* | ERROR | Record error | ERROR |

Implement as a class with:
- `transition(event: str) -> str` method that validates and executes transitions
- Event callback system for state change notifications
- Invalid transition protection (raise on invalid transitions)

## Mode Configurations

```python
MODES = {
    "quick":    {"max_rounds": 2, "max_exchanges_per_round": 5},
    "standard": {"max_rounds": 5, "max_exchanges_per_round": 10},
    "deep":     {"max_rounds": 8, "max_exchanges_per_round": 15},
}
```

## Agent Design

### Base Agent (engine/agents/base_agent.py)
- Abstract base with `generate_response(context: str, config: DebateConfig) -> AsyncGenerator[str, None]`
- Handles LLM call, streaming, token counting
- Loads prompt from prompts/*.md

### Agent A - Moderator (engine/agents/moderator_a.py)
Responsibilities:
1. TOPIC_INTRO: Introduce topic, decompose into 2 opposing perspectives, assign B/C stances
2. LEVEL_UP: Set new analytical dimension each round (tech→economic→ethics→practice, etc.)
3. SUMMARIZING: Summarize each round - B's core argument + evidence, C's core argument + evidence, fundamental vs surface disagreements, consensus points, unresolved issues
4. FINAL: Final summary of all rounds, B/C stance evolution, core contradictions
5. EXCHANGING monitoring: Detect cold start, exchange limit, deviation, factual errors

Strict prohibitions: Never express own opinion, never favor B or C, never speak for them.

### Agent B - Pro Debater (engine/agents/debater_b.py)
Each response structure:
1. 【回应对方】(30-40%): Logical analysis of C's previous argument - find logical fallacies (strawman, slippery slope, false cause, hasty generalization), point out factual errors or bias, challenge hidden assumptions
2. 【发表己见】(60-70%): Clear claim + specific evidence (data, cases, authoritative references, logical chains) + reasoning process (evidence→conclusion logic path) + analogies/historical precedents

Style: Sharp but rational, prioritize verifiable facts, acknowledge valid parts of opponent's argument.

### Agent C - Con Debater (engine/agents/debater_c.py)
Same structure as B but opposing perspective. Uses reductio ad absurdum and extreme scenario testing. Focuses on structural issues in arguments rather than edge details.

## LLM Service (engine/llm/llm_service.py)

- Unified wrapper using OpenAI Python SDK (compatible with any OpenAI-compatible API)
- Support streaming and non-streaming
- Support multiple providers via base_url + api_key configuration
- Async implementation with proper error handling and retries
- Token counting (approximate is fine)

## Model Router (engine/llm/model_router.py)

Route agents to different models:
- A → reasoning model (deepseek-r1, gpt-4o)
- B → creative model (kimi-k2, claude-sonnet)
- C → balanced model (qwen3.5-plus, gemini)

Read from .env or config. Support model fallback.

## Context Manager (engine/context_manager.py)

Build context for each LLM call:
1. System Prompt (~500 tokens) - role definition + rules + style
2. Debate meta-info (~100 tokens) - topic/round/exchange/stance/dimension
3. Current round full history (~2000 tokens) - [MOST IMPORTANT, keep complete]
4. Previous rounds compressed summaries (~500 tokens) - each round A's summary = ~100 tokens × N rounds
5. Output format instruction (~100 tokens)
6. Reserved output space (~800 tokens)

Total: ~3900 tokens (well below model context limits)

## Cold Start Detector (engine/cold_start_detector.py)

Three-dimension detection:
1. Semantic repetition: Compare last 2 messages vs previous 2 messages (cosine similarity or keyword overlap)
2. Length drop: Consecutive N messages below min_length threshold
3. Keyword repetition: High keyword repetition rate in last 6 messages

Returns True when A should intervene.

## Deviation Detector (engine/deviation_detector.py)

Check if debate has drifted from original topic:
- Method 1: Topic keyword coverage rate (extract keywords from topic vs recent messages)
- Method 2: Recent message core words vs topic word distance
- Trigger when both indicators below threshold

## TTS Service (engine/tts/tts_service.py)

- Use edge-tts (free, good Chinese quality)
- Agent voice assignments:
  - A: zh-CN-YunxiNeural (steady male)
  - B: zh-CN-YunyangNeural (powerful male)
  - C: zh-CN-XiaoxiaoNeural (intellectual female)
- Async generation, save to audio/ directory
- Return file path for playback

## CLI (cli.py)

```python
# Usage: python cli.py "AI会取代程序员吗？" [--mode quick|standard|deep] [--no-audio]
```

Features:
- Parse topic from command line
- Optional mode flag (default: standard)
- Optional --no-audio flag (skip TTS)
- Print debate in formatted text with role indicators and section markers
- Show round/dimension headers
- Save complete debate transcript to output/ directory
- Print timing stats at end

## .env.example

```
# LLM Configuration
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-xxx

# Model assignments
MODEL_A=deepseek-r1
MODEL_B=kimi-k2
MODEL_C=qwen3.5-plus

# TTS
TTS_ENGINE=edge-tts
TTS_ENABLED=true

# Audio output
AUDIO_DIR=./audio
```

## Dependencies (engine/pyproject.toml)

```toml
[project]
name = "mind-arena-engine"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "openai>=1.30.0",
    "edge-tts>=6.1.0",
    "pydantic>=2.0.0",
    "python-dotenv>=1.0.0",
    "rich>=13.0.0",      # CLI formatting
    "aiofiles>=23.0.0",
]

[project.optional-dependencies]
dev = ["pytest>=7.0.0", "pytest-asyncio>=0.23.0"]
```

## Prompts

Write the three prompt files in engine/prompts/ based on the descriptions above. They should be in Chinese (matching the debate language). Each prompt should be comprehensive (~300-500 words) and include:
- Role definition
- Strict responsibility sequence
- Output format requirements
- Style requirements
- Strict prohibitions

## Tests

### test_state_machine.py
- Test all valid state transitions
- Test invalid transition protection (should raise)
- Test pause/resume cycle
- Test stop from various states

### test_engine.py
- Test engine initialization with config
- Test mode configuration loading
- Test session creation

### test_cold_start.py
- Test semantic repetition detection
- Test length drop detection
- Test keyword repetition detection

## Important Notes

- All code should be async (asyncio)
- Use type hints throughout
- Follow the plan's exact directory structure
- Write clean, well-documented code
- The engine must be independently runnable via CLI without any server dependency
- Use `python -m engine` pattern for CLI entry
- Load .env from project root (mind-arena/.env)
- Use Rich library for CLI output formatting (colors, panels, tables)
