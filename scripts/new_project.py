#!/usr/bin/env python3
"""
Create a new video project from template.

Usage:
    python scripts/new_project.py my_video
    python scripts/new_project.py my_video --template highlights
    python scripts/new_project.py my_video -t raw-clip
"""
import argparse
import json
import sys
from pathlib import Path

# Resolve paths relative to script location
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
TEMPLATES_DIR = PROJECT_ROOT / "templates"
PROJECTS_DIR = PROJECT_ROOT / "projects"


def list_templates() -> list[str]:
    """List available templates."""
    return [d.name for d in TEMPLATES_DIR.iterdir()
            if d.is_dir() and (d / "template.json").exists()]


def create_project(name: str, template: str = "commentary") -> Path:
    """
    Create a new project from template.

    Args:
        name: Project name (will be folder name)
        template: Template to use (commentary, highlights, raw-clip)

    Returns:
        Path to created project directory
    """
    # Validate template
    template_path = TEMPLATES_DIR / template / "template.json"
    if not template_path.exists():
        available = list_templates()
        print(f"Error: Template '{template}' not found.")
        print(f"Available templates: {', '.join(available)}")
        sys.exit(1)

    # Check if project already exists
    project_dir = PROJECTS_DIR / name
    if project_dir.exists():
        print(f"Error: Project '{name}' already exists at {project_dir}")
        sys.exit(1)

    # Load template
    with open(template_path) as f:
        template_data = json.load(f)

    # Create project config from template example + defaults
    project_config = {"name": name}

    # Apply defaults
    for key, value in template_data.get("defaults", {}).items():
        project_config[key] = value

    # Apply example (overwrites defaults where specified)
    example = template_data.get("example", {})
    for key, value in example.items():
        if key != "name":  # Don't overwrite the actual project name
            project_config[key] = value

    # Update name in config
    project_config["name"] = name

    # Create project directory structure
    project_dir.mkdir(parents=True)
    (project_dir / "output").mkdir()

    # Write project.json
    project_json_path = project_dir / "project.json"
    with open(project_json_path, "w") as f:
        json.dump(project_config, f, indent=2, ensure_ascii=False)

    # Print success message with next steps
    print(f"\n{'='*60}")
    print(f"Created project: {name}")
    print(f"Template: {template}")
    print(f"Location: {project_dir}")
    print(f"{'='*60}")

    print(f"\nNext steps:")
    print(f"  1. Copy your source video to:")
    print(f"     {project_dir}/source_video.mp4")
    print(f"")
    print(f"  2. Edit project configuration:")
    print(f"     {project_json_path}")
    print(f"")

    # Template-specific instructions
    if template == "commentary":
        print(f"  3. Add your voiceover script to project.json")
        print(f"     (Use Claude Code to help write it!)")
        print(f"")
        print(f"  4. Generate the video:")
        print(f"     python skills/make-video/make_video.py {project_dir}")
    elif template == "highlights":
        print(f"  3. Find golden segments:")
        print(f"     python skills/find-golden-segments/find_golden.py {project_dir}/source_video.mp4")
        print(f"")
        print(f"  4. Review and generate:")
        print(f"     python skills/make-video/make_video.py {project_dir}")
    elif template == "raw-clip":
        print(f"  3. Set start_time and end_time in project.json")
        print(f"")
        print(f"  4. Extract the clip:")
        print(f"     python skills/extract-clip/extract.py {project_dir}")

    print(f"\n{'='*60}\n")

    return project_dir


def main():
    parser = argparse.ArgumentParser(
        description="Create a new vibecut video project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s my_video                    # Create commentary project
  %(prog)s my_video -t highlights      # Create highlights project
  %(prog)s my_video --template raw-clip # Create raw clip project
  %(prog)s --list                      # List available templates
        """
    )

    parser.add_argument(
        "name",
        nargs="?",
        help="Project name (will be the folder name)"
    )
    parser.add_argument(
        "-t", "--template",
        default="commentary",
        help="Template to use (default: commentary)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available templates"
    )

    args = parser.parse_args()

    if args.list:
        templates = list_templates()
        print("Available templates:")
        for t in templates:
            template_path = TEMPLATES_DIR / t / "template.json"
            with open(template_path) as f:
                data = json.load(f)
            desc = data.get("description", "No description")
            print(f"  {t:15} - {desc}")
        return

    if not args.name:
        parser.print_help()
        sys.exit(1)

    create_project(args.name, args.template)


if __name__ == "__main__":
    main()
