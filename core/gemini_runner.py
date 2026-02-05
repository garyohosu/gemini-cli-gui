"""
Gemini CLI Runner - Keeps Gemini CLI running as a persistent process.

Uses pywinpty for pseudo-TTY support on Windows.
"""

from __future__ import annotations

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

    def _clean_response(self, raw: str, sent_prompt: str) -> str:
        """Clean up the response by removing echoed input, prompts, and ANSI codes."""
        # First, strip ALL ANSI codes and control characters
        text = self._strip_ansi_codes(raw)
        
        lines = text.split("\n")
        cleaned_lines = []
        skip_echo = True
        found_content = False
        skip_ui_section = False

        # Patterns to skip (UI elements, banners, etc.)
        skip_patterns = [
            r'^[>›»*▀▄═─│┌┐└┘]+\s*$',  # Prompt/UI chars only
            r'^\s*$',  # Empty lines before content
            r'Waiting for auth',
            r'Press ESC or CTRL\+C',
            r'Initializing',
            r'Connecting to MCP',
            r'MCP server',
            r'YOLO mode',
            r'ctrl \+ y to toggle',
            r'no sandbox',
            r'/model',
            r'/docs',
            r'Type your message',
            r'Ready \(',
            r'Tips for getting started',
            r'Ask questions',
            r'Be specific',
            r'/help for more',
            r'^\d+\s+\w+\.md\s+files',  # "2 GEMINI.md files"
            r'^\s*[█░]+\s*$',  # ASCII art blocks
        ]

        for line in lines:
            clean_line = line.strip()

            # Skip the echoed prompt
            if skip_echo and sent_prompt.strip() in clean_line:
                skip_echo = False
                continue

            # Skip lines matching skip patterns
            should_skip = False
            for pattern in skip_patterns:
                if re.search(pattern, clean_line, re.IGNORECASE):
                    should_skip = True
                    break
            
            if should_skip:
                continue

            # Skip empty lines at the beginning
            if not found_content and not clean_line:
                continue

            # Skip lines that look like paths/directories without actual content
            # e.g., "C:\temp" alone
            if re.match(r'^[A-Z]:\\[\w\\-]+$', clean_line):
                continue

            # If we get here, it's actual content
            if clean_line:
                found_content = True
                
            cleaned_lines.append(line.rstrip())

        # Remove trailing empty lines
        while cleaned_lines and not cleaned_lines[-1].strip():
            cleaned_lines.pop()

        # Remove trailing prompt if present
        if cleaned_lines:
            last = cleaned_lines[-1].strip()
            if re.match(r'^[>›»*]\s*$', last):
                cleaned_lines.pop()

        result = "\n".join(cleaned_lines).strip()
        
        # Final cleanup: remove multiple consecutive blank lines
        result = re.sub(r'\n\n\n+', '\n\n', result)
        
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
