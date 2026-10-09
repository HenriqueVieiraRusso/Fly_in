import sys


def main(argv: list[str]) -> int:
    """Run the simulation.

    Args:
        argv: Command-line arguments, excluding the program name.

    Returns:
        Process exit code (0 on success, 1 on error).
    """
    if len(argv) != 1:
        print("Usage: python3 main.py <map_file>", file=sys.stderr)
        return 1
    print(f"Loading map: {argv[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
