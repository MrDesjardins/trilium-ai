"""Main entry point for Trilium AI."""


def main() -> None:
    """Run the Trilium AI CLI."""
    from trilium_ai.cli.commands import cli

    cli()


if __name__ == "__main__":
    main()
