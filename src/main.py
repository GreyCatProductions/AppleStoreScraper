import os
from schema.shared_state import SharedState

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "output.csv")


def main():
    state = SharedState(csv_path=CSV_PATH)
    

if __name__ == "__main__":
    main()
