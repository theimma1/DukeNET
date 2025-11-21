# AINS (Agent Identity & Naming System)

Agent registry and discovery system for DukeNET.

## Features

- Agent registration with Ed25519 signature verification
- Fast agent lookup with Redis caching (<10ms)
- Capability publishing and discovery
- Trust score calculation
- Heartbeat-based health monitoring

## Installation

pip install -e ".[dev]"



## Usage

See `examples/` for usage examples.

## Development

Run tests
pytest tests/ -v --cov=ains

Start server
uvicorn ains.api:app --reload --port 8080
