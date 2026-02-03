# gemini-cli-gui

Unofficial GUI wrapper for Gemini CLI on Windows.

## What this is
A Windows desktop app that lets you use Gemini CLI through a chat-style UI, with safety controls:
- Work only inside a selected workspace folder
- Show a preview before applying changes
- Require approval for destructive operations

This project is an AI-assisted software development experiment.

## Requirements (end users)
- Windows 10/11 (64-bit)
- Gemini CLI available on PATH
  - You will need Node.js and Gemini CLI installed
- Internet connection (Gemini communication)

## Usage
1. Download the latest exe from GitHub Releases
2. Launch the app
3. Select a workspace folder
4. Type your request in the chat
5. Review the preview and approve the changes

## Development
- Python (recommended 3.11+)
- GUI: PySide6 (or Tkinter)

## Documentation
- spec.md: technical specification and security requirements
