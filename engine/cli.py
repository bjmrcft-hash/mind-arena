"""
MindArena CLI — run a debate directly from the terminal.

Usage:
    python cli.py "AI会取代程序员吗？"
    python cli.py "远程办公是否应该成为常态？" --mode quick
    python cli.py "加密货币是未来吗？" --mode deep --no-audio
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

# Force UTF-8 on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.rule import Rule

# Load .env from project root (mind-arena/.env)
_project_root = Path(__file__).parent.parent
_env_path = _project_root / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

from engine.debate_engine import DebateEngine, DebateEvent
from engine.models.schemas import DebateConfig, MODE_PRESETS

console = Console()

# Role display config
ROLE_STYLES = {
    "A": {"name": "主持人 A", "color": "cyan", "icon": "🎤"},
    "B": {"name": "正方 B", "color": "green", "icon": "🟩"},
    "C": {"name": "反方 C", "color": "red", "icon": "🟥"},
}

MSG_TYPE_LABELS = {
    "topic_intro": "📋 话题拆解",
    "opening": "📢 开场陈述",
    "argument": "⚔️ 论点",
    "rebuttal": "🛡️ 反驳",
    "summary": "📝 轮次总结",
    "level_up": "⬆️ 维度提升",
    "verdict": "🏆 终场总结",
}


async def run_debate(topic: str, mode: str, no_audio: bool) -> None:
    """Run a debate with Rich console output."""

    config = DebateConfig(mode=mode)
    preset = MODE_PRESETS[mode]

    # Header
    console.print()
    console.print(Panel(
        f"[bold white]🏟️ MindArena[/]\n\n"
        f"话题：[bold yellow]{topic}[/]\n"
        f"模式：[bold]{mode}[/]（{preset['max_rounds']} 轮 × {preset['max_exchanges_per_round']} 交锋）\n"
        f"语音：{'❌ 关闭' if no_audio else '✅ 开启'}",
        title="[bold cyan]辩论开始[/]",
        border_style="cyan",
    ))

    engine = DebateEngine(config=config, tts_enabled=not no_audio)
    session = engine.start(topic)

    start_time = time.time()
    current_round = 0

    async for event in engine.run():
        await _handle_event(event, current_round)

        if event.event_type == "round_change" and event.round_number:
            current_round = event.round_number

    elapsed = time.time() - start_time

    # Footer
    console.print()
    console.print(Panel(
        f"[bold green]辩论完成[/]\n\n"
        f"总耗时：{elapsed:.1f} 秒\n"
        f"总消息：{len(engine.messages)} 条\n"
        f"总轮次：{engine.round_ctrl.current_round} 轮\n"
        f"总交锋：{engine.round_ctrl.total_exchanges} 次\n"
        f"状态：{session.status}",
        title="[bold cyan]统计[/]",
        border_style="green",
    ))

    # Save transcript
    _save_transcript(engine, topic, elapsed)


async def _handle_event(event: DebateEvent, current_round: int) -> None:
    """Render a single debate event to the console."""

    if event.event_type == "state_change":
        if event.state == "level_up" and event.round_number:
            console.print()
            console.print(Rule(
                f"[bold magenta]第 {event.round_number} 轮[/]",
                style="magenta",
            ))

    elif event.event_type == "round_change":
        if event.round_number:
            console.print()
            console.print(Rule(
                f"[bold magenta]第 {event.round_number} 轮[/]",
                style="magenta",
            ))

    elif event.event_type == "exchange_update":
        console.print(
            f"  [dim]── 交锋 {event.exchange_number} ──[/]"
        )

    elif event.event_type == "message_complete":
        style = ROLE_STYLES.get(event.role, ROLE_STYLES["A"])
        msg_label = MSG_TYPE_LABELS.get(event.event_type, "")

        # Build display
        role_text = Text(f"{style['icon']} {style['name']}", style=style["color"])

        content = event.content or ""
        dimension_note = ""
        if event.dimension:
            dimension_note = f" [dim]({event.dimension})[/]"

        console.print()
        console.print(f"  {role_text}{dimension_note}")

        # Indent content
        for line in content.split("\n"):
            if line.strip():
                console.print(f"    {line}")

        if event.audio_path:
            console.print(f"    [dim]🔊 {event.audio_path}[/]")

    elif event.event_type == "debate_completed":
        console.print()
        console.print("[bold green]✅ 辩论完成[/]")

    elif event.event_type == "error":
        console.print(f"[bold red]❌ 错误: {event.data.get('error', '未知')}[/]")


def _save_transcript(engine: DebateEngine, topic: str, elapsed: float) -> None:
    """Save debate transcript to output/ directory."""
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)

    import re
    safe_topic = re.sub(r'[^\w\u4e00-\u9fff]', '_', topic)[:50]
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"{safe_topic}_{timestamp}.md"
    filepath = output_dir / filename

    lines = [
        f"# MindArena 辩论记录",
        f"",
        f"**话题**: {topic}",
        f"**耗时**: {elapsed:.1f} 秒",
        f"**轮次**: {engine.round_ctrl.current_round}",
        f"**交锋**: {engine.round_ctrl.total_exchanges}",
        f"",
        f"---",
        f"",
    ]

    for msg in engine.messages:
        role_label = ROLE_STYLES[msg.role]["name"]
        msg_label = MSG_TYPE_LABELS.get(msg.message_type, msg.message_type)
        lines.append(f"## {role_label} — {msg_label}")
        lines.append(f"")
        lines.append(msg.content)
        lines.append(f"")

    filepath.write_text("\n".join(lines), encoding="utf-8")
    console.print(f"\n[dim]📄 记录已保存: {filepath}[/]")


def main():
    parser = argparse.ArgumentParser(
        description="MindArena — 多 LLM 辩论系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python cli.py "AI会取代程序员吗？"
  python cli.py "远程办公是否应该成为常态？" --mode quick
  python cli.py "加密货币是未来吗？" --mode deep --no-audio
        """,
    )
    parser.add_argument("topic", help="辩论话题")
    parser.add_argument(
        "--mode", choices=["quick", "standard", "deep"],
        default="standard",
        help="辩论模式 (默认: standard)",
    )
    parser.add_argument(
        "--no-audio", action="store_true",
        help="关闭 TTS 语音合成",
    )

    args = parser.parse_args()
    asyncio.run(run_debate(args.topic, args.mode, args.no_audio))


if __name__ == "__main__":
    main()
