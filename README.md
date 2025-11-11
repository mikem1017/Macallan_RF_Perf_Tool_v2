# Macallan RF Performance Tool v2

A full-featured RF performance analysis tool for plotting S-parameters and comparing measurements against specifications to determine pass/fail status for individual serial numbers.

## Features

- **Device Maintenance**: CRUD operations for device configurations and test criteria
- **Test Setup**: Load and analyze RF measurement files (Touchstone S2P-S10P)
- **Plotting**: Interactive plotting with filtering, axis controls, and export capabilities
- **Compliance Testing**: Automatic pass/fail evaluation against device specifications

## Requirements

- Python 3.13.7+ (Python 3.14 preferred)
- See `requirements.txt` for dependencies

## Installation

```bash
pip install -r requirements.txt
```

For development:

```bash
pip install -r requirements-dev.txt
```

## Architecture

This application is built with testability as the highest priority, using:

- **Clean Architecture**: Strict separation between data layer, business logic, and UI
- **Repository Pattern**: Abstract interfaces for data access, enabling easy testing
- **Dependency Injection**: Services receive dependencies via constructor for testability
- **Modular Design**: Test types are pluggable via abstract base classes

## Project Structure

```
src/
├── core/           # Core business logic (UI-independent, fully testable)
├── gui/            # UI layer (thin, delegates to services)
└── database/       # Database schema and migrations

tests/
├── unit/           # Unit tests (no GUI)
├── integration/    # Integration tests
└── gui/            # GUI tests (pytest-qt)
```

## Running Tests

```bash
pytest
```

With coverage:

```bash
pytest --cov=src --cov-report=html
```

## License

Proprietary - Macallan Engineering










