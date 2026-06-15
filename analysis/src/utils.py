import re


def extract_country_code(text: str) -> str | None:
    match = re.search(r'apple\.com[/_]([a-z]{2})[/_]', text)
    return match.group(1) if match else None


def reconstruct_url(filename: str) -> str | None:
    app_id = re.search(r'id(\d+)', filename)
    if not app_id:
        return None
    cc = extract_country_code(filename)
    if cc:
        return f"https://apps.apple.com/{cc}/app/id{app_id.group(1)}"
    return f"https://apps.apple.com/app/id{app_id.group(1)}"

if __name__ == "__main__":
    import sys
    url = sys.argv[1] if len(sys.argv) > 1 else "https://apps.apple.com/us/app/%D8%A3%D8%B0%D9%83%D8%A7%D8%B1-%D8%A7%D9%84%D9%85%D8%B3%D9%84%D9%85-%D8%B5%D9%84%D8%A7%D8%A9-%D9%88%D8%AA%D8%B3%D8%A8%D9%8A%D8%AD/id6760594235"
    print(reconstruct_url(url))