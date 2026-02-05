"""
Gemini CLI Runner - Keeps Gemini CLI running as a persistent process.

Uses pywinpty for pseudo-TTY support on Windows.
"""

from __future__ import annotations

import re
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
    _process: Optional[winpty.PtyProcess] = field(default=None, init=False, repr=False)
    _running: bool = field(default=False, init=False)
    _buffer: str = field(default="", init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _read_thread: Optional[threading.Thread] = field(default=None, init=False, repr=False)
    _on_output: Optional[Callable[[str], None]] = field(default=None, init=False, repr=False)

    # Pattern to detect end of response (prompt ready for next input)
    # Gemini CLI shows various prompts like "> ", "gemini> ", etc.
    PROMPT_PATTERN = re.compile(r'\n[>›»] $|\n\x1b\[\d*m[>›»]\x1b\[0m $', re.MULTILINE)

    def start(self, on_output: Optional[Callable[[str], None]] = None) -> bool:
        """Start the Gemini CLI process."""
        if self._running:
            return True

        self._on_output = on_output

        try:
            # Build command
            cmd = "gemini"
            if self.yolo_mode:
                cmd += " -y"

            # Create PTY with reasonable size
            self._pty = winpty.PTY(cols=200, rows=50)

            # Spawn process
            self._process = self._pty.spawn(cmd, cwd=str(self.working_dir))
            self._running = True
            self._buffer = ""

            # Start reader thread
            self._read_thread = threading.Thread(target=self._reader_loop, daemon=True)
            self._read_thread.start()

            # Wait for initial prompt
            self._wait_for_prompt(timeout=60.0)

            return True

        except Exception as e:
            self._running = False
            if self._on_output:
                self._on_output(f"[ERROR] Failed to start Gemini CLI: {e}\n")
            return False

    def stop(self) -> None:
        """Stop the Gemini CLI process."""
        self._running = False

        if self._process:
            try:
                # Send exit command
                self._pty.write("/exit\r\n")
                time.sleep(0.5)
            except Exception:
                pass

            try:
                self._process.terminate()
            except Exception:
                pass

        self._process = None
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
            escaped_prompt = prompt.replace("\\", "\\\\").replace("\r", "").replace("\n", " ")
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
        return self._running and self._process is not None

    def _reader_loop(self) -> None:
        """Background thread that reads from PTY."""
        while self._running and self._pty:
            try:
                data = self._pty.read(timeout=100)  # 100ms timeout
                if data:
                    with self._lock:
                        self._buffer += data
                    if self._on_output:
                        self._on_output(data)
            except winpty.WinptyError:
                # Timeout or closed, continue
                pass
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

            # Check for prompt pattern
            if self.PROMPT_PATTERN.search(current_buffer):
                return current_buffer

            # Also check for simple prompt patterns
            if current_buffer.rstrip().endswith(">") or current_buffer.rstrip().endswith("›"):
                # Wait a bit more to ensure it's stable
                stable_count += 1
                if stable_count >= 3:
                    return current_buffer
            else:
                stable_count = 0

            # Check if buffer is growing
            if len(current_buffer) == last_buffer_len:
                stable_count += 1
                if stable_count >= 10:  # 1 second of no output
                    # Check if we have meaningful content
                    if len(current_buffer) > 10:
                        return current_buffer
            else:
                stable_count = 0
                last_buffer_len = len(current_buffer)

            time.sleep(0.1)

        raise TimeoutError("Timed out waiting for prompt")

    def _clean_response(self, raw: str, sent_prompt: str) -> str:
        """Clean up the response by removing echoed input and prompts."""
        lines = raw.split("\n")
        cleaned_lines = []
        skip_echo = True

        for line in lines:
            # Remove ANSI escape codes for comparison
            clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line)
            clean_line = clean_line.strip()

            # Skip the echoed prompt
            if skip_echo and sent_prompt.strip() in clean_line:
                skip_echo = False
                continue

            # Skip empty lines at the beginning
            if not cleaned_lines and not clean_line:
                continue

            # Skip prompt lines
            if re.match(r'^[>›»]\s*$', clean_line):
                continue

            # Remove ANSI codes from actual line
            cleaned = re.sub(r'\x1b\[[0-9;]*m', '', line)
            cleaned_lines.append(cleaned)

        # Remove trailing empty lines and prompt
        while cleaned_lines and not cleaned_lines[-1].strip():
            cleaned_lines.pop()

        # Remove trailing prompt if present
        if cleaned_lines:
            last = cleaned_lines[-1].strip()
            if re.match(r'^[>›»]\s*$', last):
                cleaned_lines.pop()

        return "\n".join(cleaned_lines).strip()


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
