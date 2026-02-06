"""
CLI verification app for persistent Gemini CLI over TTY (pywinpty).

Usage examples:
  py scripts/verify_gemini_tty.py --prompt "Say hello in one word."
  py scripts/verify_gemini_tty.py --prompt "Explain E=mc^2 in one sentence." --repeat 3
  py scripts/verify_gemini_tty.py --interactive
"""

from __future__ import annotations

import argparse
import re
import sys
import threading
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.gemini_runner import GeminiRunner  # noqa: E402


class OutputCollector:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._buffer: list[str] = []

    def append(self, chunk: str) -> None:
        with self._lock:
            self._buffer.append(chunk)

    def reset(self) -> None:
        with self._lock:
            self._buffer = []

    def snapshot(self) -> str:
        with self._lock:
            return "".join(self._buffer)


def _escape_controls(text: str, max_chars: int = 800) -> str:
    """Escape control characters so raw output can be previewed safely."""
    if len(text) > max_chars:
        text = text[:max_chars] + "...(truncated)"

    def repl(match: re.Match[str]) -> str:
        ch = match.group(0)
        return f"\\x{ord(ch):02x}"

    # Escape ESC explicitly, then any remaining control characters
    text = text.replace("\x1b", "\\x1b")
    return re.sub(r"[\x00-\x1f\x7f-\x9f]", repl, text)


def _safe_print(text: str) -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        safe = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
        print(safe)


def _ensure_parent(path: Path) -> None:
    if path.parent and not path.parent.exists():
        path.parent.mkdir(parents=True, exist_ok=True)


def run_prompts(
    runner: GeminiRunner,
    collector: OutputCollector,
    prompts: list[str],
    timeout: float,
    show_clean: bool,
    show_raw_preview: bool,
    raw_log: Path | None,
    clean_log: Path | None,
) -> int:
    exit_code = 0
    for idx, prompt in enumerate(prompts, start=1):
        collector.reset()
        response = runner.send_prompt(prompt, timeout=timeout)
        raw = collector.snapshot()

        ansi_count = raw.count("\x1b")
        cleaned = response.text

        print(
            f"[{idx}] elapsed_ms={response.elapsed_ms} "
            f"raw_len={len(raw)} ansi_esc={ansi_count} "
            f"clean_len={len(cleaned)} success={response.success}"
        )

        if response.error:
            print(f"[{idx}] error={response.error}")
            exit_code = 1

        if show_raw_preview:
            print("[raw-preview]")
            _safe_print(_escape_controls(raw))

        if show_clean:
            print("[cleaned]")
            _safe_print(cleaned)

        if raw_log:
            _ensure_parent(raw_log)
            with raw_log.open("a", encoding="utf-8") as f:
                f.write(f"\n--- prompt {idx} ---\n")
                f.write(raw)
                f.write("\n")

        if clean_log:
            _ensure_parent(clean_log)
            with clean_log.open("a", encoding="utf-8") as f:
                f.write(f"\n--- prompt {idx} ---\n")
                f.write(cleaned)
                f.write("\n")

    return exit_code


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify persistent Gemini CLI over TTY (pywinpty)."
    )
    parser.add_argument(
        "--working-dir",
        default=str(Path.cwd()),
        help="Workspace directory to run Gemini in.",
    )
    parser.add_argument(
        "--prompt",
        default="Say hello in one word.",
        help="Prompt to send (ignored in --interactive mode).",
    )
    parser.add_argument(
        "--repeat",
        type=int,
        default=1,
        help="Number of times to send the prompt.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=180.0,
        help="Timeout (seconds) per prompt.",
    )
    parser.add_argument(
        "--no-yolo",
        action="store_true",
        help="Disable YOLO (-y) mode.",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Interactive mode (type prompts; blank line or /exit to quit).",
    )
    parser.add_argument(
        "--show-raw-preview",
        action="store_true",
        help="Show escaped preview of raw output (includes ANSI).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress cleaned response output.",
    )
    parser.add_argument(
        "--raw-log",
        default="",
        help="Append raw output to this file.",
    )
    parser.add_argument(
        "--clean-log",
        default="",
        help="Append cleaned output to this file.",
    )

    args = parser.parse_args()

    working_dir = Path(args.working_dir)
    if not working_dir.exists():
        print(f"Working directory not found: {working_dir}", file=sys.stderr)
        return 2

    raw_log = Path(args.raw_log) if args.raw_log else None
    clean_log = Path(args.clean_log) if args.clean_log else None

    collector = OutputCollector()
    runner = GeminiRunner(working_dir=working_dir, yolo_mode=not args.no_yolo)

    try:
        runner.start(on_output=collector.append)
    except Exception as exc:
        print(f"Failed to start GeminiRunner: {exc}", file=sys.stderr)
        return 1

    try:
        if args.interactive:
            print("Interactive mode: enter prompt (blank line or /exit to quit)")
            while True:
                try:
                    user_input = input("> ").strip()
                except EOFError:
                    break
                if not user_input or user_input.lower() in {"/exit", "/quit"}:
                    break
                run_prompts(
                    runner=runner,
                    collector=collector,
                    prompts=[user_input],
                    timeout=args.timeout,
                    show_clean=not args.quiet,
                    show_raw_preview=args.show_raw_preview,
                    raw_log=raw_log,
                    clean_log=clean_log,
                )
        else:
            prompts = [args.prompt] * max(args.repeat, 1)
            return run_prompts(
                runner=runner,
                collector=collector,
                prompts=prompts,
                timeout=args.timeout,
                show_clean=not args.quiet,
                show_raw_preview=args.show_raw_preview,
                raw_log=raw_log,
                clean_log=clean_log,
            )
    finally:
        runner.stop()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
