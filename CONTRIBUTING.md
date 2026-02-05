# Contributing to Multi-Agent SQL Pipeline

Thank you for your interest in contributing! This project is a blueprint for professional-grade multi-agent architectures.

## How to Contribute

1. **Fork the Repo**: Create your own copy of the repository.
2. **Create a Branch**: Work on a descriptive branch (e.g., `feature/add-oracle-hints`).
3. **Follow Best Practices**:
    - Use the `BaseAgent` class for new agents.
    - Modularize logic into the appropriate `common_files/` utility.
    - Write unit tests for new utility functions.
4. **Submit a PR**: Provide a clear description of your changes and why they are necessary.

## Code Standards
- **Modularity**: Avoid monolithic files.
- **Typing**: Use Python type hints wherever possible.
- **Documentation**: Update the README if you introduce structural changes.

## Testing
Please ensure all tests pass before submitting your PR:
```bash
pytest
```