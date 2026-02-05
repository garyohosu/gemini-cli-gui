"""
Gemini CLI Runner - Keeps Gemini CLI running as a persistent process.

Uses pywinpty for pseudo-TTY support on Windows.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import winpty


@dataclass
class GeminiResponse:
    """Response from Gemini CLI."""
    text: str
    elapsed_ms: int
    success: bool = True
    error: Optional[str] = None


@dataclass
class GeminiRunner:
    """
    Manages a persistent Gemini CLI process using pseudo-TTY.

    Usage:
        runner = GeminiRunner(working_dir=Path("C:/myproject"))
        runner.start()
        response = runner.send_prompt("Hello")
        print(response.text)
        runner.stop()
    """
    working_dir: Path
    yolo_mode: bool = True
    _pty: Optional[winpty.PTY] = field(default=None, init=False, repr=False)
    _spawned: bool = field(default=False, init=False)
    _running: bool = field(default=False, init=False)
    _buffer: str = field(default="", init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _read_thread: Optional[threading.Thread] = field(default=None, init=False, repr=False)
    _on_output: Optional[Callable[[str], None]] = field(default=None, init=False, repr=False)

    # Pattern to detect end of response (prompt ready for next input)
    # Gemini CLI shows various prompts like "> ", "gemini> ", etc.
    PROMPT_PATTERN = re.compile(r'[>›»]\s*$', re.MULTILINE)
    UI_PATTERNS = [
        re.compile(r'^[>›»*▀▄═─│┌┐└┘├┤┬┴┼╭╮╰╯╔╗╚╝╠╣╦╩╬═║]+$'),
        re.compile(r'Waiting for auth', re.IGNORECASE),
        re.compile(r'Press ESC or CTRL\+C', re.IGNORECASE),
        re.compile(r'Initializing', re.IGNORECASE),
        re.compile(r'Connecting to MCP', re.IGNORECASE),
        re.compile(r'MCP server', re.IGNORECASE),
        re.compile(r'YOLO mode', re.IGNORECASE),
        re.compile(r'ctrl \+ y to toggle', re.IGNORECASE),
        re.compile(r'no sandbox', re.IGNORECASE),
        re.compile(r'/model', re.IGNORECASE),
        re.compile(r'/docs', re.IGNORECASE),
        re.compile(r'Type your message', re.IGNORECASE),
        re.compile(r'Ready \(', re.IGNORECASE),
        re.compile(r'Tips for getting started', re.IGNORECASE),
        re.compile(r'Ask questions', re.IGNORECASE),
        re.compile(r'Be specific', re.IGNORECASE),
        re.compile(r'/help for more', re.IGNORECASE),
        re.compile(r'^\d+\s+\w+\.md\s+files$', re.IGNORECASE),
        re.compile(r'^\s*[█░]+\s*$'),
        re.compile(r'^\s*[▀▄]+\s*$'),
    ]

    def start(self, on_output: Optional[Callable[[str], None]] = None) -> bool:
        """Start the Gemini CLI process."""
        if self._running:
            return True

        self._on_output = on_output

        try:
            # Find gemini command
            gemini_path = shutil.which("gemini")
            if not gemini_path:
                # Try gemini.cmd on Windows
                gemini_path = shutil.which("gemini.cmd")

            if not gemini_path:
                raise FileNotFoundError("gemini command not found in PATH")

            # Build command line arguments
            cmdline = ""
            if self.yolo_mode:
                cmdline = "-y"

            # Create PTY with reasonable size
            self._pty = winpty.PTY(cols=200, rows=50)

            # Spawn process using cmd.exe to handle .cmd files properly
            # appname: full path to executable
            # cmdline: arguments
            # cwd: working directory
            cmd_exe = os.environ.get("COMSPEC", "cmd.exe")
            full_cmdline = f'/c "{gemini_path}" {cmdline}'

            self._spawned = self._pty.spawn(
                appname=cmd_exe,
                cmdline=full_cmdline,
                cwd=str(self.working_dir)
            )

            if not self._spawned:
                raise RuntimeError("Failed to spawn gemini process")

            self._running = True
            self._buffer = ""

            # Start reader thread
            self._read_thread = threading.Thread(target=self._reader_loop, daemon=True)
            self._read_thread.start()

            # Wait for initial prompt
            self._wait_for_prompt(timeout=120.0)

            return True

        except Exception as e:
            self._running = False
            self._spawned = False
            if self._on_output:
                self._on_output(f"[ERROR] Failed to start Gemini CLI: {e}\n")
            raise

    def stop(self) -> None:
        """Stop the Gemini CLI process."""
        self._running = False

        if self._pty and self._spawned:
            try:
                # Send exit command
                self._pty.write("/exit\r\n")
                time.sleep(0.5)
            except Exception:
                pass

        self._spawned = False
        self._pty = None
        self._buffer = ""

    def send_prompt(self, prompt: str, timeout: float = 300.0) -> GeminiResponse:
        """
        Send a prompt and wait for response.

        Args:
            prompt: The prompt to send
            timeout: Maximum time to wait for response in seconds

        Returns:
            GeminiResponse with the response text
        """
        if not self._running or not self._pty:
            return GeminiResponse(
                text="",
                elapsed_ms=0,
                success=False,
                error="Gemini CLI is not running"
            )

        start_time = time.monotonic()

        try:
            with self._lock:
                # Clear buffer before sending
                self._buffer = ""

            # Send the prompt (add newline to submit)
            # Escape any special characters
            escaped_prompt = prompt.replace("\r", "").replace("\n", " ")
            self._pty.write(escaped_prompt + "\r\n")

            # Wait for response (until next prompt appears)
            response_text = self._wait_for_prompt(timeout=timeout)

            elapsed_ms = int((time.monotonic() - start_time) * 1000)

            # Clean up the response
            cleaned = self._clean_response(response_text, prompt)

            return GeminiResponse(
                text=cleaned,
                elapsed_ms=elapsed_ms,
                success=True
            )

        except TimeoutError:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return GeminiResponse(
                text="",
                elapsed_ms=elapsed_ms,
                success=False,
                error="Response timeout"
            )
        except Exception as e:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return GeminiResponse(
                text="",
                elapsed_ms=elapsed_ms,
                success=False,
                error=str(e)
            )

    def is_running(self) -> bool:
        """Check if the Gemini CLI process is running."""
        return self._running and self._spawned

    def _reader_loop(self) -> None:
        """Background thread that reads from PTY."""
        while self._running and self._pty:
            try:
                # Use non-blocking read
                data = self._pty.read(blocking=False)
                if data:
                    with self._lock:
                        self._buffer += data
                    if self._on_output:
                        self._on_output(data)
                else:
                    # No data available, sleep briefly
                    time.sleep(0.05)
            except winpty.WinptyError:
                # PTY closed or error
                if self._running:
                    time.sleep(0.1)
            except Exception:
                if self._running:
                    time.sleep(0.1)

    def _wait_for_prompt(self, timeout: float) -> str:
        """Wait until the prompt appears, indicating response is complete."""
        deadline = time.monotonic() + timeout
        last_buffer_len = 0
        stable_count = 0

        while time.monotonic() < deadline:
            with self._lock:
                current_buffer = self._buffer

            # Check for prompt pattern at end of buffer
            stripped = current_buffer.rstrip()
            if stripped.endswith(">") or stripped.endswith("›") or stripped.endswith("»"):
                # Wait a bit more to ensure it's stable
                stable_count += 1
                if stable_count >= 5:  # 0.5 seconds of stability
                    return current_buffer
            else:
                # Check if buffer stopped growing (response complete)
                if len(current_buffer) == last_buffer_len and len(current_buffer) > 0:
                    stable_count += 1
                    if stable_count >= 20:  # 2 seconds of no output
                        return current_buffer
                else:
                    stable_count = 0
                    last_buffer_len = len(current_buffer)

            time.sleep(0.1)

        raise TimeoutError("Timed out waiting for prompt")

    def _strip_ansi_codes(self, text: str) -> str:
        """
        Comprehensively remove ANSI escape sequences and control characters.
        
        This handles:
        - CSI sequences (colors, cursor movement, etc.)
        - OSC sequences (window title, etc.)
        - Other escape sequences
        - Control characters (except newline, carriage return, tab)
        """
        # Remove CSI sequences: ESC [ ... letter
        text = re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', text)
        
        # Remove OSC sequences: ESC ] ... (terminated by BEL or ESC \)
        text = re.sub(r'\x1B\].*?(?:\x07|\x1B\\)', '', text)
        
        # Remove other ESC sequences: ESC letter or ESC # letter
        text = re.sub(r'\x1B[@-Z\\-_]', '', text)
        text = re.sub(r'\x1B#[0-9]', '', text)
        
        # Remove control characters except \n, \r, \t
        text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F-\x9F]', '', text)
        
        # Remove common box drawing and special characters that appear in UI
        # (These are usually part of the Gemini CLI UI, not actual content)
        text = re.sub(r'[─│┌┐└┘├┤┬┴┼╭╮╰╯╔╗╚╝╠╣╦╩╬═║]', '', text)
        
        # Remove spinner characters
        text = re.sub(r'[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]', '', text)
        
        return text

    def _is_ui_line(self, line: str) -> bool:
        """Return True if the line looks like Gemini CLI UI/banners, not content."""
        for pattern in self.UI_PATTERNS:
            if pattern.search(line):
                return True
        return False

    def _clean_response(self, raw: str, sent_prompt: str) -> str:
        """Clean up the response by removing echoed input, prompts, and ANSI codes."""
        logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
        logger = logging.getLogger(__name__)
        logger.debug("=== CLEAN RESPONSE START ===")
        logger.debug("Raw length: %d", len(raw))
        logger.debug("Sent prompt: %s", sent_prompt)

        # First, strip ALL ANSI codes and control characters
        text = self._strip_ansi_codes(raw)
        logger.debug("After ANSI strip: %d chars", len(text))
        logger.debug("First 300 chars:\n%s", text[:300])

        lines = text.split("\n")
        prompt = sent_prompt.strip()
        response_lines: list[str] = []
        state = "searching"

        for i, line in enumerate(lines):
            stripped = line.strip()

            if state == "searching":
                if prompt and prompt in stripped:
                    state = "found_prompt"
                    logger.debug("Found prompt at line %d", i)
                continue

            if state == "found_prompt":
                if not stripped:
                    continue
                if self._is_ui_line(stripped):
                    logger.debug("Skipping UI line after prompt: %s", stripped[:80])
                    continue
                state = "collecting"
                response_lines.append(line.rstrip())
                logger.debug("Response starts: %s", stripped[:120])
                continue

            if state == "collecting":
                if stripped in [">", "›", "»", "*"] or re.match(r'^[>›»]\s*$', stripped):
                    logger.debug("Detected prompt at line %d", i)
                    break
                if self._is_ui_line(stripped):
                    continue
                response_lines.append(line.rstrip())

        result = "\n".join(response_lines).strip()
        result = re.sub(r'\n\n\n+', '\n\n', result)

        if not result:
            logger.debug("State machine produced empty result; falling back to loose cleanup")
            fallback_lines: list[str] = []
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue
                if prompt and prompt in stripped:
                    continue
                if self._is_ui_line(stripped):
                    continue
                if re.match(r'^[A-Z]:\\[\w\\-]+$', stripped):
                    continue
                fallback_lines.append(line.rstrip())
            result = "\n".join(fallback_lines).strip()
            result = re.sub(r'\n\n\n+', '\n\n', result)

        logger.debug("Final result: %s", result)
        logger.debug("=== CLEAN RESPONSE END ===")

        return result


# Singleton instance for app-wide use
_runner_instance: Optional[GeminiRunner] = None


def get_runner() -> Optional[GeminiRunner]:
    """Get the global GeminiRunner instance."""
    return _runner_instance


def create_runner(working_dir: Path, yolo_mode: bool = True) -> GeminiRunner:
    """Create and set the global GeminiRunner instance."""
    global _runner_instance
    if _runner_instance:
        _runner_instance.stop()
    _runner_instance = GeminiRunner(working_dir=working_dir, yolo_mode=yolo_mode)
    return _runner_instance


def stop_runner() -> None:
    """Stop the global GeminiRunner instance."""
    global _runner_instance
    if _runner_instance:
        _runner_instance.stop()
        _runner_instance = None
