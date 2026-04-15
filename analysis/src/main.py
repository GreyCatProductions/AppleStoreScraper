import os
from typing import List


PATH_TO_DATA_FOLDER = os.path.join(os.path.dirname(__file__), "../dataLoader")

def main():
    if not os.path.exists(PATH_TO_DATA_FOLDER):
        raise FileNotFoundError(f"Expected data to be in {PATH_TO_DATA_FOLDER}! Folder not found.")
    
    for root, dirs, files in os.walk(PATH_TO_DATA_FOLDER):
        for file in files:
            path = os.path.join(root, file)
            #TODO: do stuff