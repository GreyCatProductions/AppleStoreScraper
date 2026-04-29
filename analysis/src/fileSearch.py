import os
import re
import sys


def search(root: str, pattern: str):
    regex = re.compile(pattern)

    if not os.path.exists(root):
        print(f"Path does not exist: {root}", file=sys.stderr)
        sys.exit(1)

    if os.path.isfile(root):
        count = 1 if regex.search(os.path.basename(root)) else 0
    else:
        count = 0
        for _, _, files in os.walk(root):
            for name in files:
                if regex.search(name):
                    count += 1

    print(count)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python fileSearch.py <path> <regex>")
        sys.exit(1)
    search(sys.argv[1], sys.argv[2])
