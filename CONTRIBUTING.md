# Contributing to bitnet-hub

Thanks for your interest in contributing! This project is in early development and help is very welcome.

## Getting Started

```bash
git clone https://github.com/YOUR_USERNAME/bitnet-hub.git
cd bitnet-hub
pip install -e ".[dev]"
```

## Project Structure

```
bitnet-hub/
├── bitnet_hub/
│   ├── __init__.py          # Package version
│   ├── cli.py               # Click CLI commands
│   ├── config.py            # Paths and constants
│   ├── registry.py          # Model catalog loader
│   └── registry.json        # Known BitNet models
├── tests/
├── pyproject.toml           # Package config
├── README.md
├── CONTRIBUTING.md
└── LICENSE
```

## Roadmap

See the README for the current phase. Pick an unimplemented TODO in the codebase and open a PR!

## Guidelines

- Keep it simple — this should be easy for anyone to install and use
- Follow the existing code style
- Add comments explaining *why*, not just *what*
- Test your changes before submitting a PR
