import os
import re
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class GeminiResponse:
    success: bool
    response_text: str
    elapsed_seconds: float
    output_file: str
    error: str = ""


class GeminiFileClient:
    def __init__(self, output_dir: Optional[str] = None, workspace_dir: Optional[str] = None) -> None:
        self.output_dir = output_dir or os.path.join(
            os.environ.get("TEMP", r"C:\temp"),
            "gemini_output",
        )
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
        self.workspace_dir = workspace_dir

        self.ps_script = Path(__file__).parent.parent / "scripts" / "run_gemini_to_file.ps1"
        if not self.ps_script.exists():
            raise FileNotFoundError(f"PowerShell script not found: {self.ps_script}")

    def send_prompt(self, prompt: str, timeout: int = 180, workspace_dir: Optional[str] = None) -> GeminiResponse:
        output_file = os.path.join(
            self.output_dir,
            f"gemini_{uuid.uuid4().hex[:8]}.txt",
        )
        
        # Use provided workspace_dir or fallback to instance workspace_dir
        workspace = workspace_dir or self.workspace_dir

        start_time = time.time()
        try:
            args = [
                "powershell.exe",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(self.ps_script),
                "-Prompt",
                prompt,
                "-OutputFile",
                output_file,
                "-TimeoutSeconds",
                str(timeout),
            ]
            
            # Add workspace directory if specified
            if workspace:
                args.extend(["-WorkspaceDir", str(workspace)])
            
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout + 10,
                cwd=str(self.ps_script.parent.parent),
            )

            elapsed = time.time() - start_time

            if os.path.exists(output_file):
                # Try to read with mbcs (Windows default) or utf-8
                try:
                    with open(output_file, "r", encoding="mbcs", errors="replace") as file_handle:
                        raw_output = file_handle.read()
                except Exception:
                    with open(output_file, "r", encoding="utf-8", errors="replace") as file_handle:
                        raw_output = file_handle.read()

                error_text = self._detect_error(raw_output)
                if error_text:
                    return GeminiResponse(
                        success=False,
                        response_text="",
                        elapsed_seconds=elapsed,
                        output_file=output_file,
                        error=error_text,
                    )

                clean_output = self._clean_response(raw_output)
                if not clean_output:
                    return GeminiResponse(
                        success=False,
                        response_text="",
                        elapsed_seconds=elapsed,
                        output_file=output_file,
                        error="Empty response after cleaning",
                    )

                return GeminiResponse(
                    success=True,
                    response_text=clean_output,
                    elapsed_seconds=elapsed,
                    output_file=output_file,
                )

            error_message = result.stderr.strip() if result.stderr else "Output file not found"
            return GeminiResponse(
                success=False,
                response_text="",
                elapsed_seconds=elapsed,
                output_file=output_file,
                error=error_message,
            )
        except subprocess.TimeoutExpired:
            elapsed = time.time() - start_time
            return GeminiResponse(
                success=False,
                response_text="",
                elapsed_seconds=elapsed,
                output_file=output_file,
                error=f"Timeout after {timeout} seconds",
            )
        except Exception as exc:
            elapsed = time.time() - start_time
            return GeminiResponse(
                success=False,
                response_text="",
                elapsed_seconds=elapsed,
                output_file=output_file,
                error=str(exc),
            )

    def _clean_response(self, text: str) -> str:
        # Remove ANSI escape sequences
        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        text = ansi_escape.sub("", text)

        skip_patterns = [
            r"^\s*$",
            r"Waiting for auth",
            r"Initializing",
            r"Loading",
            r"YOLO mode is enabled",
            r"Loaded cached credentials",
            r"Hook registry initialized",
            r"Server '.*' supports tool updates",
            r"Attempt \d+ failed:",
            r"Gemini",
            r"is not recognized as an internal or external command",
            r"Press ESC or CTRL\+C",
        ]

        clean_lines = []
        for line in text.splitlines():
            if any(re.search(pattern, line) for pattern in skip_patterns):
                continue
            clean_lines.append(line)

        return "\n".join(clean_lines).strip()

    def _detect_error(self, text: str) -> str:
        lowered = text.lower()
        if "is not recognized as an internal or external command" in lowered:
            return "Gemini CLI not found in PATH"
        if "exhausted your capacity" in lowered:
            return "Gemini CLI capacity exhausted"
        return ""
