# Contributing to vibecut

Thank you for your interest in contributing!

## Ways to Contribute

1. **Report bugs** - Open an issue describing the problem
2. **Suggest features** - Open an issue with your idea
3. **Add new skills** - Create modular skills for new capabilities
4. **Improve documentation** - Help make the project more accessible
5. **Share examples** - Show what you've built with vibecut

## Development Setup

```bash
# Clone and install
git clone https://github.com/yourusername/vibecut.git
cd vibecut
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
ruff check .
```

## Creating a New Skill

Skills are modular capabilities in the `skills/` directory.

### Skill Structure

```
skills/my-new-skill/
├── SKILL.md          # Documentation (required)
├── my_skill.py       # Main implementation
└── requirements.txt  # Additional dependencies (optional)
```

### SKILL.md Template

```markdown
# Skill Name

Brief description of what this skill does.

## Usage

\`\`\`bash
python skills/my-new-skill/my_skill.py [arguments]
\`\`\`

## Input

- What inputs the skill expects

## Output

- What outputs the skill produces

## Dependencies

- Any external services or APIs required

## Examples

Show example usage and output.
```

### Skill Best Practices

1. **Single responsibility** - Each skill does one thing well
2. **Clear interfaces** - Use consistent input/output formats
3. **Graceful errors** - Use `config.require()` for API dependencies
4. **Documentation** - Always include a SKILL.md

## Code Style

- **Python**: Follow PEP 8, use type hints
- **TypeScript**: Use strict mode, prefer functional patterns
- **Comments**: Explain *why*, not *what*

## Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Run tests and linting
5. Commit with clear messages
6. Open a pull request

## Commit Messages

Use clear, descriptive commit messages:

```
Add voice-clone skill for Qwen3-TTS

- Implement voice embedding upload
- Add speech generation with style prompts
- Include max_new_tokens for long audio
```

## Questions?

Open an issue or start a discussion. We're happy to help!
