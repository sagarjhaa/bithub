"""Interactive chat REPL for bithub."""

import json
import sys
import time
from typing import List, Optional, Tuple

import httpx
from rich.console import Console
from rich.markdown import Markdown

console = Console()


def is_slash_command(text: str) -> bool:
    """Check if input is a slash command."""
    return bool(text) and text.startswith("/")


def parse_slash_command(text: str) -> Tuple[str, str]:
    """Parse a slash command into (command, argument)."""
    parts = text[1:].split(None, 1)
    cmd = parts[0] if parts else ""
    arg = parts[1] if len(parts) > 1 else ""
    return cmd, arg


class ChatSession:
    """Manages conversation state for the REPL."""

    def __init__(self, model: str, api_url: str) -> None:
        self.model = model
        self.api_url = api_url.rstrip("/")
        self.messages: List[dict] = []
        self.system_prompt: Optional[str] = None
        self.total_tokens = 0

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})

    def clear(self) -> None:
        self.messages.clear()
        self.total_tokens = 0

    def set_system_prompt(self, prompt: str) -> None:
        self.system_prompt = prompt

    def build_payload(self) -> dict:
        msgs: List[dict] = []
        if self.system_prompt:
            msgs.append({"role": "system", "content": self.system_prompt})
        msgs.extend(self.messages)
        return {
            "model": self.model,
            "messages": msgs,
            "stream": True,
        }

    def export(self) -> str:
        lines = []
        for msg in self.messages:
            lines.append(f"{msg['role']}: {msg['content']}")
        return "\n\n".join(lines)

    def send_and_stream(self) -> str:
        """Send current conversation to API and stream the response.

        Returns the full assistant response text.
        """
        payload = self.build_payload()
        url = f"{self.api_url}/v1/chat/completions"
        full_response = ""

        try:
            with httpx.stream("POST", url, json=payload, timeout=120.0) as response:
                if response.status_code != 200:
                    console.print(f"[red]API error: {response.status_code}[/red]")
                    return ""

                for line in response.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            sys.stdout.write(content)
                            sys.stdout.flush()
                            full_response += content
                    except json.JSONDecodeError:
                        continue

        except httpx.ConnectError:
            console.print("[red]Cannot connect to API server.[/red]")
            console.print("Is the server running? Start with: bithub serve <model>")
        except httpx.ReadTimeout:
            console.print("\n[yellow]Response timed out.[/yellow]")

        sys.stdout.write("\n")
        return full_response


HELP_TEXT = """[bold]Available commands:[/bold]
  /help              Show this help
  /clear             Clear conversation history
  /system <prompt>   Set system prompt
  /model             Show current model info
  /export            Save conversation to file
  /quit              Exit chat
"""


def handle_slash_command(cmd: str, arg: str, session: ChatSession) -> Optional[str]:
    """Handle a slash command. Returns 'quit' to exit, None otherwise."""
    if cmd == "help":
        console.print(HELP_TEXT)
    elif cmd == "clear":
        session.clear()
        console.print("[dim]Conversation cleared.[/dim]")
    elif cmd == "system":
        if not arg:
            if session.system_prompt:
                console.print(f"[dim]Current system prompt: {session.system_prompt}[/dim]")
            else:
                console.print("[dim]No system prompt set. Usage: /system <prompt>[/dim]")
        else:
            session.set_system_prompt(arg)
            console.print("[dim]System prompt set.[/dim]")
    elif cmd == "model":
        console.print(f"[bold]Model:[/bold] {session.model}")
        console.print(f"[bold]API:[/bold] {session.api_url}")
        console.print(f"[bold]Messages:[/bold] {len(session.messages)}")
        console.print(f"[bold]Tokens:[/bold] ~{session.total_tokens}")
    elif cmd == "export":
        filename = arg if arg else f"chat-{int(time.time())}.txt"
        content = session.export()
        if not content:
            console.print("[yellow]Nothing to export.[/yellow]")
        else:
            with open(filename, "w") as f:
                f.write(content)
            console.print(f"[green]Saved to {filename}[/green]")
    elif cmd in ("quit", "exit", "q"):
        return "quit"
    else:
        console.print(f"[yellow]Unknown command: /{cmd}[/yellow]")
        console.print("Type [bold]/help[/bold] for available commands.")
    return None


def start_repl(model: str, api_url: str) -> None:
    """Start the interactive REPL."""
    try:
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import FileHistory
        from bithub.config import BITHUB_HOME

        history_file = BITHUB_HOME / "repl_history"
        BITHUB_HOME.mkdir(parents=True, exist_ok=True)
        prompt_session: Optional[PromptSession] = PromptSession(
            history=FileHistory(str(history_file))
        )
    except ImportError:
        prompt_session = None

    session = ChatSession(model=model, api_url=api_url)

    console.print(f"[bold green]Chat with {model}[/bold green]")
    console.print(f"[dim]API: {api_url} | Type /help for commands | Ctrl+D to exit[/dim]\n")

    while True:
        try:
            if prompt_session:
                user_input = prompt_session.prompt(f"[{model}] > ")
            else:
                user_input = input(f"[{model}] > ")
        except (EOFError, KeyboardInterrupt):
            console.print("\n[green]Goodbye![/green]")
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        if is_slash_command(user_input):
            cmd, arg = parse_slash_command(user_input)
            result = handle_slash_command(cmd, arg, session)
            if result == "quit":
                console.print("[green]Goodbye![/green]")
                break
            continue

        # Send message to API
        session.add_message("user", user_input)
        console.print()
        response = session.send_and_stream()
        if response:
            session.add_message("assistant", response)
        console.print()
