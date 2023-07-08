"""Command-line interface."""
import click


@click.command()
@click.version_option()
def main() -> None:
    """Notion Assistant."""


if __name__ == "__main__":
    main(prog_name="notion-assistant")  # pragma: no cover
