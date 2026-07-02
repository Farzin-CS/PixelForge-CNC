# Contributing to PixelForge CNC

## Development Setup

1. Clone the repo:
   ```bash
   git clone https://github.com/Farzin-CS/PixelForge-CNC.git
   cd PixelForge-CNC
   ```

2. Install in editable mode:
   ```bash
   pip install -e .
   pip install -r requirements.txt
   ```

3. Run the app:
   ```bash
   python run.py
   ```

## Running Tests

```bash
pip install pytest ruff
pytest -v
ruff check .
```

## Code Style

- Line length: 100
- Target: Python 3.10+
- Use `from __future__ import annotations` in all files
- Type-hint all function signatures

## Pull Request Process

1. Open an issue first describing the change
2. Fork and create a feature branch
3. Add tests for any new functionality
4. Ensure all tests pass and lint is clean
5. Submit the PR with a clear description
