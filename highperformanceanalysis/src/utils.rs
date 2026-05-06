use regex::Regex;
use std::sync::OnceLock;

pub fn extract_country_code(text: &str) -> Option<&str> {
    static RE: OnceLock<Regex> = OnceLock::new();
    let re = RE.get_or_init(|| Regex::new(r"apple\.com[/_]([a-z]{2})[/_]").unwrap());
    re.captures(text)?.get(1).map(|m| m.as_str())
}

pub fn reconstruct_url(text: &str) -> Option<String> {
    static RE: OnceLock<Regex> = OnceLock::new();
    let re = RE.get_or_init(|| Regex::new(r"id(\d+)").unwrap());
    let app_id = re.captures(text)?.get(1)?.as_str();
    match extract_country_code(text) {
        Some(cc) => Some(format!("https://apps.apple.com/{cc}/app/id{app_id}")),
        None => Some(format!("https://apps.apple.com/app/id{app_id}")),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_country_code() {
        assert_eq!(
            extract_country_code("https://apps.apple.com/us/app/foo/id123"),
            Some("us")
        );
        assert_eq!(
            extract_country_code("https://apps.apple.com/de/app/foo/id123"),
            Some("de")
        );
        assert_eq!(extract_country_code("no_country_here"), None);
    }

    #[test]
    fn test_reconstruct_url_with_country() {
        assert_eq!(
            reconstruct_url("https://apps.apple.com/us/app/foo/id6760594235"),
            Some("https://apps.apple.com/us/app/id6760594235".to_string())
        );
    }

    #[test]
    fn test_reconstruct_url_without_country() {
        assert_eq!(
            reconstruct_url("some_file_id12345.html"),
            Some("https://apps.apple.com/app/id12345".to_string())
        );
    }

    #[test]
    fn test_reconstruct_url_no_id() {
        assert_eq!(reconstruct_url("no_app_id_here.html"), None);
    }
}
