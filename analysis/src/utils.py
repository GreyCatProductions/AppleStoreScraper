import re


def reconstruct_url(filename: str) -> str | None:
    match = re.search(r'id(\d+)', filename)
    if match:
        return f"https://apps.apple.com/app/id{match.group(1)}"
    return None

if __name__ == "__main__":
    url = "https://apps.apple.com/us/app/%D8%A3%D8%B0%D9%83%D8%A7%D8%B1-%D8%A7%D9%84%D9%85%D8%B3%D9%84%D9%85-%D8%B5%D9%84%D8%A7%D8%A9-%D9%88%D8%AA%D8%B3%D8%A8%D9%8A%D8%AD/id6760594235"
    print(reconstruct_url(url))