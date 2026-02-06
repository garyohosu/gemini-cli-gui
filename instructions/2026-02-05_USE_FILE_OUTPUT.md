# Gemini CLI File Output Implementation Guide

**Date**: 2026-02-05  
**Author**: GenSpark AI (automated)  
**Purpose**: Implement Gemini CLI wrapper using file output for reliable response extraction

---

## 🎯 Background

### Previous Attempts
1. ❌ **pywinpty + pyte**: Failed due to TUI character table output
2. ❌ **subprocess + stream-json**: 30+ seconds per request (unacceptable)

### New Approach: File Output
- ✅ Use PowerShell to redirect Gemini CLI output to file
- ✅ Read file after command completion
- ✅ Simple, reliable, proven by smoke.vbs

---

## 📋 Implementation Steps

### Step 1: Create PowerShell Script

**File**: `scripts/run_gemini_to_file.ps1`

```powershell
param(
    [string]$Prompt,
    [string]$OutputFile = "C:\temp\gemini_output.txt",
    [int]$TimeoutSeconds = 180
)

# Create output directory
$outDir = Split-Path -Parent $OutputFile
if (-not (Test-Path $outDir)) {
    New-Item -ItemType Directory -Path $outDir -Force | Out-Null
}

# Remove existing output file
if (Test-Path $OutputFile) {
    Remove-Item $OutputFile -Force
}

# Run Gemini CLI with output redirection
$command = "gemini -p `"$Prompt`" -y > `"$OutputFile`" 2>&1"
$proc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", $command -WindowStyle Hidden -PassThru

# Wait for completion
$proc | Wait-Process -Timeout $TimeoutSeconds

# Read output file
if (Test-Path $OutputFile) {
    Get-Content $OutputFile -Raw
} else {
    Write-Error "Output file not found: $OutputFile"
    exit 1
}
```

### Step 2: Create Python Client

**File**: `core/gemini_file_client.py`

```python
import subprocess
import time
import os
import re
import uuid
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

@dataclass
class GeminiResponse:
    """Response from Gemini CLI"""
    success: bool
    response_text: str
    elapsed_seconds: float
    output_file: str
    error: str = ""

class GeminiFileClient:
    """Gemini CLI wrapper using file output"""
    
    def __init__(self, output_dir: Optional[str] = None):
        """Initialize client with output directory"""
        self.output_dir = output_dir or os.path.join(
            os.environ.get('TEMP', 'C:\\temp'), 
            'gemini_output'
        )
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
        
        # PowerShell script path
        self.ps_script = Path(__file__).parent.parent / "scripts" / "run_gemini_to_file.ps1"
        
        if not self.ps_script.exists():
            raise FileNotFoundError(f"PowerShell script not found: {self.ps_script}")
    
    def send_prompt(self, prompt: str, timeout: int = 180) -> GeminiResponse:
        """
        Send prompt to Gemini CLI and get response from file
        
        Args:
            prompt: User prompt
            timeout: Timeout in seconds (default: 180)
        
        Returns:
            GeminiResponse with success status and response text
        """
        # Generate unique output filename
        output_file = os.path.join(
            self.output_dir, 
            f"gemini_{uuid.uuid4().hex[:8]}.txt"
        )
        
        start_time = time.time()
        
        try:
            # Run PowerShell script
            result = subprocess.run(
                [
                    "powershell.exe",
                    "-ExecutionPolicy", "Bypass",
                    "-File", str(self.ps_script),
                    "-Prompt", prompt,
                    "-OutputFile", output_file,
                    "-TimeoutSeconds", str(timeout)
                ],
                capture_output=True,
                text=True,
                timeout=timeout + 10,
                cwd=str(self.ps_script.parent.parent)
            )
            
            elapsed = time.time() - start_time
            
            # Read output file
            if os.path.exists(output_file):
                with open(output_file, 'r', encoding='utf-8', errors='ignore') as f:
                    raw_output = f.read()
                
                # Clean response
                clean_output = self._clean_response(raw_output)
                
                return GeminiResponse(
                    success=True,
                    response_text=clean_output,
                    elapsed_seconds=elapsed,
                    output_file=output_file
                )
            else:
                return GeminiResponse(
                    success=False,
                    response_text="",
                    elapsed_seconds=elapsed,
                    output_file=output_file,
                    error="Output file not found"
                )
        
        except subprocess.TimeoutExpired:
            elapsed = time.time() - start_time
            return GeminiResponse(
                success=False,
                response_text="",
                elapsed_seconds=elapsed,
                output_file=output_file,
                error=f"Timeout after {timeout} seconds"
            )
        except Exception as e:
            elapsed = time.time() - start_time
            return GeminiResponse(
                success=False,
                response_text="",
                elapsed_seconds=elapsed,
                output_file=output_file,
                error=str(e)
            )
    
    def _clean_response(self, text: str) -> str:
        """
        Clean Gemini CLI output
        
        - Remove ANSI escape sequences
        - Remove ASCII art logo
        - Remove status messages
        """
        # Remove ANSI escape sequences
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        text = ansi_escape.sub('', text)
        
        # Split into lines
        lines = text.split('\n')
        clean_lines = []
        
        skip_patterns = [
            r'^\s*$',  # Empty lines
            r'Waiting for auth',
            r'Initializing',
            r'Loading',
            r'───',  # Separator lines
            r'│',    # Box drawing
            r'Gemini',  # Logo
        ]
        
        for line in lines:
            # Skip lines matching patterns
            if any(re.search(pattern, line) for pattern in skip_patterns):
                continue
            
            clean_lines.append(line)
        
        return '\n'.join(clean_lines).strip()
```

### Step 3: Create CLI Verification Script

**File**: `scripts/verify_file_client.py`

```python
#!/usr/bin/env python3
"""
CLI verification for GeminiFileClient
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.gemini_file_client import GeminiFileClient

def main():
    """Run verification tests"""
    print("=" * 60)
    print("Gemini File Client Verification")
    print("=" * 60)
    
    client = GeminiFileClient()
    
    test_cases = [
        ("Say hello", "Simple greeting"),
        ("Count to 3", "Simple counting"),
        ("こんにちは", "Japanese greeting"),
        ("What is 2+2?", "Simple math"),
    ]
    
    results = []
    
    for i, (prompt, description) in enumerate(test_cases, 1):
        print(f"\n[Test {i}/{len(test_cases)}] {description}")
        print(f"Prompt: {prompt}")
        print("-" * 60)
        
        # Run 3 times to verify consistency
        for run in range(1, 4):
            print(f"  Run {run}... ", end="", flush=True)
            
            response = client.send_prompt(prompt, timeout=180)
            
            result = {
                'test': i,
                'run': run,
                'description': description,
                'prompt': prompt,
                'success': response.success,
                'elapsed': response.elapsed_seconds,
                'response_len': len(response.response_text),
                'response': response.response_text[:200],  # First 200 chars
                'output_file': response.output_file,
                'error': response.error
            }
            results.append(result)
            
            if response.success:
                print(f"✅ {response.elapsed_seconds:.2f}s | {len(response.response_text)} chars")
                if run == 1:
                    print(f"\n--- Response Preview ---")
                    print(response.response_text[:300])
                    print("..." if len(response.response_text) > 300 else "")
                    print("-" * 60)
            else:
                print(f"❌ {response.error}")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    success_count = sum(1 for r in results if r['success'])
    total_count = len(results)
    avg_time = sum(r['elapsed'] for r in results if r['success']) / max(success_count, 1)
    
    print(f"Success Rate: {success_count}/{total_count} ({100*success_count/total_count:.1f}%)")
    print(f"Average Time: {avg_time:.2f}s")
    
    if success_count == total_count:
        print("\n✅ ALL TESTS PASSED")
        return 0
    else:
        print(f"\n❌ {total_count - success_count} TESTS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

---

## 🧪 Testing Instructions

### Run CLI Verification

```bash
cd C:\PROJECT\gemini-cli-gui
python scripts\verify_file_client.py
```

### Expected Results

```
[Test 1/4] Simple greeting
Prompt: Say hello
------------------------------------------------------------
  Run 1... ✅ 32.5s | 15 chars

--- Response Preview ---
Hello! 👋
------------------------------------------------------------
  Run 2... ✅ 28.3s | 15 chars
  Run 3... ✅ 27.9s | 15 chars
...
```

### Success Criteria

- ✅ All tests pass (success_count == total_count)
- ✅ Response length > 0 for all runs
- ✅ Response text contains expected content
- ✅ Average time < 60 seconds

---

## 📊 Document Results

Create: `result/2026-02-05_file_output_verification.md`

```markdown
# Gemini File Output Verification Results

**Date**: 2026-02-05
**Method**: PowerShell file redirection

## Test Results

[Paste output from verify_file_client.py]

## Analysis

- Success Rate: X/Y (Z%)
- Average Response Time: N seconds
- Response Quality: [Good/Poor]

## Conclusion

[✅ PASS / ❌ FAIL]

## Next Steps

- [ ] If all tests pass: Integrate into app.py
- [ ] If tests fail: Document errors and investigate
```

---

## 🔗 GUI Integration (if tests pass)

### Update `app.py`

Replace `GeminiRunner` with `GeminiFileClient`:

```python
from core.gemini_file_client import GeminiFileClient

class MainWindow(QMainWindow):
    def __init__(self):
        # ...
        self.gemini_client = GeminiFileClient()
    
    def _send_message_impl(self):
        # ...
        response = self.gemini_client.send_prompt(
            user_message,
            timeout=180
        )
        
        if response.success:
            self._add_message(response.response_text, is_user=False)
        else:
            self._add_message(f"Error: {response.error}", is_user=False)
```

---

## ✅ Completion Checklist

- [ ] Create `scripts/run_gemini_to_file.ps1`
- [ ] Create `core/gemini_file_client.py`
- [ ] Create `scripts/verify_file_client.py`
- [ ] Run CLI verification
- [ ] Document results in `result/2026-02-05_file_output_verification.md`
- [ ] If tests pass: Integrate into `app.py`
- [ ] Test GUI with file output method
- [ ] Update CHANGELOG.md
- [ ] Commit and push to branch

---

## 📝 Notes

### Advantages
- ✅ Simple and reliable
- ✅ No PTY/TUI issues
- ✅ Easy to debug (just read the file)
- ✅ Proven approach (smoke.vbs)

### Trade-offs
- ⚠️ ~30 seconds per request (Gemini CLI startup)
- ⚠️ Requires file I/O
- ⚠️ Needs cleanup of temp files

### Future Improvements
- Add file cleanup mechanism
- Optimize timeout settings
- Add progress indication
