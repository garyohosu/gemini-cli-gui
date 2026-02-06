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
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

import pyte
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
    # Terminal emulator for screen restoration
    _screen: Optional[pyte.HistoryScreen] = field(default=None, init=False, repr=False)
    _stream: Optional[pyte.Stream] = field(default=None, init=False, repr=False)

    # Pattern to detect end of response (prompt ready for next input)
    # Gemini CLI shows various prompts like "> ", "gemini> ", etc.
    PROMPT_PATTERN = re.compile(r'[>›»]\s*$', re.MULTILINE)
    
    UI_PATTERNS = [
        re.compile(r'^[>›»*▀▄═─│┌┐└┘├┤┬┴┼╭╮╰╯╔╗╚╝╠╣╦╩╬═║\s█░]+$'),
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
        re.compile(r'^\d+\s+\w+\.md\s+files', re.IGNORECASE),
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

            # Initialize terminal emulator
            with self._lock:
                self._screen = pyte.HistoryScreen(
                    columns=200,
                    lines=50,
                    history=5000
                )
                self._stream = pyte.Stream(self._screen)

            # Spawn process using cmd.exe to handle .cmd files properly
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

            # Wait for initial prompt (must be patient during startup)
            self._wait_for_prompt(timeout=120.0, require_prompt=True)

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
                if self._screen:
                    self._screen.reset()

            # Send the prompt (add newline to submit)
            escaped_prompt = prompt.replace("\n", "\\n")
            self._pty.write(f"{escaped_prompt}\n")

            # Wait for response (until next prompt appears)
            self._wait_for_prompt(timeout=timeout)

            elapsed_ms = int((time.monotonic() - start_time) * 1000)

            # Clean up the response using screen dump (restores terminal state)
            screen_dump = self._dump_screen_text()
            cleaned = self._clean_response(screen_dump, prompt)

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
                        if self._stream:
                            self._stream.feed(data)
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

    def _wait_for_prompt(self, timeout: float, require_prompt: bool = False) -> str:
        """Wait until the prompt appears, indicating response is complete."""
        deadline = time.monotonic() + timeout
        last_buffer_len = 0
        stable_count = 0
        start_time = time.monotonic()

        while time.monotonic() < deadline:
            with self._lock:
                current_buffer = self._buffer

            # Check for prompt pattern at end of buffer
            stripped = current_buffer.rstrip()
            
            # Simple check for prompt characters at the end
            if stripped.endswith(">") or stripped.endswith("›") or stripped.endswith("»") or stripped.endswith("*"):
                # Wait a bit more to ensure it's stable
                stable_count += 1
                if stable_count >= 5:  # 0.5 seconds of stability
                    return current_buffer
            else:
                # During initial startup, we MUST wait for a prompt character.
                # During normal prompts, we can fall back to stability after a while.
                elapsed = time.monotonic() - start_time
                if not require_prompt or elapsed > 10.0:
                    # Check if buffer stopped growing (response complete)
                    if len(current_buffer) == last_buffer_len and len(current_buffer) > 0:
                        stable_count += 1
                        # Wait longer for stability if we haven't seen a prompt
                        if stable_count >= 30:  # 3 seconds of no output
                            return current_buffer
                    else:
                        stable_count = 0
                        last_buffer_len = len(current_buffer)

            time.sleep(0.1)

        raise TimeoutError("Timed out waiting for prompt")

    def _strip_ansi_codes(self, text: str) -> str:
        """Comprehensively remove ANSI escape sequences and control characters."""
        # Remove CSI sequences: ESC [ ... letter
        text = re.sub(r'\x1B\[[0-?]*[ -/]*[@-~]', '', text)
        # Remove OSC sequences: ESC ] ... (terminated by BEL or ESC \)
        text = re.sub(r'\x1B\].*?(?:\x07|\x1B\\)', '', text)
        # Remove other ESC sequences
        text = re.sub(r'\x1B[@-Z\\-_]', '', text)
        text = re.sub(r'\x1B#[0-9]', '', text)
        # Remove control characters except \n, \r, \t
        text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F-\x9F]', '', text)
        # Remove common box drawing characters
        text = re.sub(r'[─│┌┐└┘├┤┬┴┼╭╮╰╯╔╗╚╝╠╣╦╩╬═║]', '', text)
        # Remove spinner characters
        text = re.sub(r'[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]', '', text)
        return text

    def _is_ui_line(self, line: str) -> bool:
        """Return True if the line looks like Gemini CLI UI/banners, not content."""
        if not line.strip():
            return False
        for pattern in self.UI_PATTERNS:
            if pattern.search(line):
                return True
        return False

    def _dump_screen_text(self) -> str:
        """Dump current screen content as text from pyte buffer."""
        if not self._screen:
            return ""

        def _line_to_text(line) -> str:
            if isinstance(line, str):
                return line.rstrip()
            
            chars = []
            if isinstance(line, dict):
                # pyte 0.8.0+ buffer line
                for x in range(self._screen.columns):
                    char = line.get(x)
                    chars.append(char.data if char else " ")
            else:
                # list of Char (history)
                for char in line:
                    chars.append(char.data if hasattr(char, "data") else str(char))
            
            return "".join(chars).rstrip()

        with self._lock:
            lines = []
            # Scrollback
            for line in self._screen.history.top:
                lines.append(_line_to_text(line))
            # Visible screen
            for y in range(self._screen.lines):
                line_data = self._screen.buffer.get(y)
                lines.append(_line_to_text(line_data) if line_data else "")
            return "\n".join(lines)

    def _clean_response(self, raw: str, sent_prompt: str) -> str:
        """Clean up response using a state machine to extract actual content."""
        if not raw:
            return ""

        # Strip ANSI codes first
        text = self._strip_ansi_codes(raw)
        lines = text.split("\n")
        
        # State machine
        state = "searching"  # searching -> found_prompt -> collecting -> done
        response_lines = []
        
        logging.debug(f"=== _clean_response start (raw len: {len(raw)}) ===")
        
        for i, line in enumerate(lines):
            stripped = line.strip()
            
            if state == "searching":
                # Find echoed prompt
                if sent_prompt.strip() in stripped:
                    state = "found_prompt"
                    logging.debug(f"Line {i}: Found prompt: {stripped[:50]}")
                    continue
            
            elif state == "found_prompt":
                # Skip empty lines immediately after prompt
                if not stripped:
                    continue
                # Skip UI lines
                if self._is_ui_line(stripped):
                    continue
                # This is the start of actual response!
                state = "collecting"
                response_lines.append(line.rstrip())
                logging.debug(f"Line {i}: Response starts: {stripped[:50]}")
            
            elif state == "collecting":
                # Stop at next prompt symbol on a line by itself
                if stripped in ['>', '›', '»', '*']:
                    state = "done"
                    logging.debug(f"Line {i}: Found next prompt, stopping.")
                    break
                # Skip UI lines within response
                if self._is_ui_line(stripped):
                    continue
                # Collect response line
                response_lines.append(line.rstrip())
        
        # Fallback: if nothing collected, return all non-UI, non-prompt lines
        if not response_lines:
            logging.debug("Fallback: No lines collected by state machine")
            for line in lines:
                stripped = line.strip()
                if stripped and not self._is_ui_line(stripped) and sent_prompt.strip() not in stripped:
                    response_lines.append(line.rstrip())
        
        result = "\n".join(response_lines).strip()
        result = re.sub(r'\n\n\n+', '\n\n', result)
        logging.debug(f"Extracted {len(result)} chars")
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