"""Tests for bithub.repl."""

from typing import List
from unittest.mock import patch, MagicMock

import pytest


class TestMessageHistory:
    def test_add_user_message(self) -> None:
        from bithub.repl import ChatSession
        session = ChatSession(model="test-model", api_url="http://localhost:8080")
        session.add_message("user", "hello")
        assert len(session.messages) == 1
        assert session.messages[0] == {"role": "user", "content": "hello"}

    def test_add_assistant_message(self) -> None:
        from bithub.repl import ChatSession
        session = ChatSession(model="test-model", api_url="http://localhost:8080")
        session.add_message("assistant", "hi there")
        assert len(session.messages) == 1
        assert session.messages[0]["role"] == "assistant"

    def test_clear_messages(self) -> None:
        from bithub.repl import ChatSession
        session = ChatSession(model="test-model", api_url="http://localhost:8080")
        session.add_message("user", "hello")
        session.add_message("assistant", "hi")
        session.clear()
        assert len(session.messages) == 0

    def test_system_prompt(self) -> None:
        from bithub.repl import ChatSession
        session = ChatSession(model="test-model", api_url="http://localhost:8080")
        session.set_system_prompt("You are a pirate.")
        session.add_message("user", "hello")
        payload = session.build_payload()
        assert payload["messages"][0]["role"] == "system"
        assert payload["messages"][0]["content"] == "You are a pirate."
        assert payload["messages"][1]["role"] == "user"

    def test_build_payload(self) -> None:
        from bithub.repl import ChatSession
        session = ChatSession(model="test-model", api_url="http://localhost:8080")
        session.add_message("user", "hello")
        payload = session.build_payload()
        assert payload["model"] == "test-model"
        assert payload["messages"] == [{"role": "user", "content": "hello"}]
        assert payload["stream"] is True


class TestSlashCommands:
    def test_is_command(self) -> None:
        from bithub.repl import is_slash_command
        assert is_slash_command("/help") is True
        assert is_slash_command("/clear") is True
        assert is_slash_command("hello") is False
        assert is_slash_command("") is False

    def test_parse_system_command(self) -> None:
        from bithub.repl import parse_slash_command
        cmd, arg = parse_slash_command("/system You are helpful")
        assert cmd == "system"
        assert arg == "You are helpful"

    def test_parse_command_no_arg(self) -> None:
        from bithub.repl import parse_slash_command
        cmd, arg = parse_slash_command("/clear")
        assert cmd == "clear"
        assert arg == ""

    def test_parse_help(self) -> None:
        from bithub.repl import parse_slash_command
        cmd, arg = parse_slash_command("/help")
        assert cmd == "help"


class TestExportConversation:
    def test_export_to_string(self) -> None:
        from bithub.repl import ChatSession
        session = ChatSession(model="test-model", api_url="http://localhost:8080")
        session.add_message("user", "hello")
        session.add_message("assistant", "hi there")
        exported = session.export()
        assert "user: hello" in exported
        assert "assistant: hi there" in exported
