use ego_tree::NodeRef;
use regex::Regex;
use scraper::{ElementRef, Html, Selector, node::Node};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::sync::OnceLock;

#[derive(Debug, Serialize, Deserialize, Default)]
pub struct AppData {
    pub url: String,
    pub app_name: Option<String>,
    pub developer_name: Option<String>,
    pub category: Option<String>,
    pub price: Option<String>,
    pub description: Option<String>,
    pub similar_apps: Vec<String>,
    pub review_count: Option<String>,
    pub review_average: Option<String>,
    pub review_one: Option<i32>,
    pub review_two: Option<i32>,
    pub review_three: Option<i32>,
    pub review_four: Option<i32>,
    pub review_five: Option<i32>,
    pub versions: Option<String>,
    pub size: Option<u64>,
    pub languages: Option<String>,
    pub age: Option<String>,
    pub age_reasons: Vec<String>,
    pub privacy_linked: Vec<String>,
    pub privacy_unlinked: Vec<String>,
    pub privacy_tracked: Vec<String>,
    pub privacy_not_collected: String,
    pub version_history: Vec<VersionEntry>,
    pub in_app_purchases: Option<String>,
    pub privacy_policy_link: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct VersionEntry {
    pub version: String,
    pub date: String,
    pub notes: Option<String>,
}

fn get_nested(data: &Value, keys: &[&str]) -> Option<String> {
    let mut cur = data;
    for &k in keys {
        cur = cur.get(k)?;
    }
    match cur {
        Value::Null => None,
        Value::String(s) => {
            let t = s.trim();
            (!t.is_empty()).then(|| t.to_string())
        }
        other => Some(other.to_string()),
    }
}

fn next_in_order(node: NodeRef<Node>) -> Option<NodeRef<Node>> {
    if let Some(child) = node.first_child() {
        return Some(child);
    }
    let mut cur = node;
    loop {
        if let Some(sib) = cur.next_sibling() {
            return Some(sib);
        }
        cur = cur.parent()?;
    }
}

fn find_next_by_tag<'a>(start: ElementRef<'a>, tag: &str) -> Option<ElementRef<'a>> {
    let mut cur: NodeRef<'a, Node> = *start;
    loop {
        cur = next_in_order(cur)?;
        if let Some(el) = ElementRef::wrap(cur) {
            if el.value().name() == tag {
                return Some(el);
            }
        }
    }
}

fn find_next_matching<'a, F>(start: ElementRef<'a>, f: F) -> Option<ElementRef<'a>>
where
    F: Fn(ElementRef<'a>) -> bool,
{
    let mut cur: NodeRef<'a, Node> = *start;
    loop {
        cur = next_in_order(cur)?;
        if let Some(el) = ElementRef::wrap(cur) {
            if f(el) {
                return Some(el);
            }
        }
    }
}

fn find_dt<'a>(doc: &'a Html, labels: &[&str]) -> Option<ElementRef<'a>> {
    static SEL: OnceLock<Selector> = OnceLock::new();
    let sel = SEL.get_or_init(|| Selector::parse("dt").unwrap());
    doc.select(sel).find(|el| {
        let raw = el.text().collect::<String>();
        let text = raw.trim().to_lowercase();
        labels.iter().any(|&l| text == l)
    })
}

fn el_text(el: ElementRef<'_>, sep: &str) -> String {
    el.text()
        .map(str::trim)
        .filter(|s| !s.is_empty())
        .collect::<Vec<_>>()
        .join(sep)
}

fn size_to_bytes(text: &str) -> Option<u64> {
    static RE: OnceLock<Regex> = OnceLock::new();
    let re = RE.get_or_init(|| Regex::new(r"(?i)([\d.,]+)\s*(b|kb|mb|gb)").unwrap());
    let s = text.replace('\u{a0}', " ").replace(',', ".");
    let caps = re.captures(&s)?;
    let num: f64 = caps[1].parse().ok()?;
    let mult: f64 = match caps[2].to_uppercase().as_str() {
        "B" => 1.0,
        "KB" => 1_000.0,
        "MB" => 1_000_000.0,
        "GB" => 1_000_000_000.0,
        _ => return None,
    };
    Some((num * mult) as u64)
}

fn privacy_items(doc: &Html, labels: &[&str]) -> Vec<String> {
    static H2: OnceLock<Selector> = OnceLock::new();
    static LI: OnceLock<Selector> = OnceLock::new();
    let h2_sel = H2.get_or_init(|| Selector::parse("h2").unwrap());
    let li_sel = LI.get_or_init(|| Selector::parse("li").unwrap());

    let h2 = doc
        .select(h2_sel)
        .filter(|el| {
            let raw = el.text().collect::<String>();
            let t = raw.trim();
            labels.iter().any(|&l| t == l)
        })
        .nth(1);

    let h2 = match h2 {
        Some(h) => h,
        None => return vec![],
    };
    let ul = match find_next_by_tag(h2, "ul") {
        Some(u) => u,
        None => return vec![],
    };
    ul.select(li_sel).map(|li| el_text(li, " ")).collect()
}


pub fn extract_app_refs(doc: &Html) -> Vec<String> {
    static SEL: OnceLock<Selector> = OnceLock::new();
    static RE: OnceLock<Regex> = OnceLock::new();
    let sel = SEL.get_or_init(|| Selector::parse("a[href]").unwrap());
    let re =
        RE.get_or_init(|| Regex::new(r"^https://apps\.apple\.com/[a-z]{2}/app/.+/id\d+$").unwrap());
    doc.select(sel)
        .filter_map(|a| a.value().attr("href"))
        .filter(|href| re.is_match(href))
        .map(str::to_string)
        .collect()
}

pub fn extract_app_data(url: &str, html: &str) -> Option<AppData> {
    let doc = Html::parse_document(html);

    static SCRIPT_SEL: OnceLock<Selector> = OnceLock::new();
    let script_sel = SCRIPT_SEL.get_or_init(|| {
        Selector::parse(r#"script[id="software-application"][type="application/ld+json"]"#).unwrap()
    });
    let json_text = doc.select(script_sel).next()?.text().collect::<String>();
    let data: Value = serde_json::from_str(&json_text).ok()?;

    let app_name = get_nested(&data, &["name"]);
    let developer = get_nested(&data, &["author", "name"]);
    let category = get_nested(&data, &["applicationCategory"]);
    let price = match (
        get_nested(&data, &["offers", "price"]),
        get_nested(&data, &["offers", "priceCurrency"]),
    ) {
        (Some(p), Some(c)) => Some(format!("{p} {c}")),
        (Some(p), None) => Some(p),
        _ => None,
    };
    let review_average = get_nested(&data, &["aggregateRating", "ratingValue"]);
    let review_count = get_nested(&data, &["aggregateRating", "reviewCount"]);
    let description = get_nested(&data, &["description"]);

    static STAR_SEL: OnceLock<Selector> = OnceLock::new();
    static STAR_RE: OnceLock<Regex> = OnceLock::new();
    let star_sel =
        STAR_SEL.get_or_init(|| Selector::parse(r#"[class*="numbers__star-graph__row"]"#).unwrap());
    let star_re = STAR_RE.get_or_init(|| Regex::new(r"(\d) star, (\d+)%").unwrap());
    let mut ratings: [Option<i32>; 5] = [None; 5];
    for el in doc.select(star_sel) {
        let label = el.value().attr("aria-label").unwrap_or_default();
        if let Some(caps) = star_re.captures(label) {
            if let (Ok(stars), Ok(pct)) = (caps[1].parse::<usize>(), caps[2].parse::<i32>()) {
                if (1..=5).contains(&stars) {
                    ratings[stars - 1] = Some(pct);
                }
            }
        }
    }

    static LANG_SEL: OnceLock<Selector> = OnceLock::new();
    let lang_sel = LANG_SEL.get_or_init(|| Selector::parse("ul li .styled-text").unwrap());
    let languages = find_dt(&doc, &["languages", "sprachen"])
        .and_then(|dt| find_next_by_tag(dt, "details"))
        .and_then(|d| d.select(lang_sel).next())
        .map(|el| el_text(el, ""))
        .filter(|s| !s.is_empty());

    static SIZE_SEL: OnceLock<Selector> = OnceLock::new();
    let size_sel = SIZE_SEL.get_or_init(|| Selector::parse("li .styled-text").unwrap());
    let size = find_dt(&doc, &["size", "größe"])
        .and_then(|dt| find_next_by_tag(dt, "ul"))
        .and_then(|ul| ul.select(size_sel).next())
        .map(|el| el_text(el, ""))
        .and_then(|t| size_to_bytes(&t));

    static COMPAT_SEL: OnceLock<Selector> = OnceLock::new();
    let compat_sel = COMPAT_SEL.get_or_init(|| Selector::parse("ul li .styled-text").unwrap());
    let versions = find_dt(&doc, &["kompatibilität", "compatibility"])
        .and_then(|dt| find_next_by_tag(dt, "details"))
        .map(|d| {
            d.select(compat_sel)
                .map(|b| el_text(b, "\n"))
                .filter(|s| !s.is_empty())
                .collect::<Vec<_>>()
                .join("|")
        })
        .filter(|s| !s.is_empty());

    static IAP_SEL: OnceLock<Selector> = OnceLock::new();
    let iap_sel = IAP_SEL.get_or_init(|| Selector::parse("ul li").unwrap());
    let in_app_purchases = find_dt(&doc, &["in\u{2011}app purchases", "in-app-käufe"])
        .and_then(|dt| find_next_by_tag(dt, "details"))
        .map(|d| {
            d.select(iap_sel)
                .map(|b| el_text(b, "\n"))
                .filter(|s| !s.is_empty())
                .collect::<Vec<_>>()
                .join("|")
        })
        .filter(|s| !s.is_empty());

    let age = find_dt(&doc, &["age rating", "altersfreigabe"])
        .and_then(|dt| {
            find_next_matching(dt, |el| {
                let name = el.value().name();
                if name != "div" && name != "span" {
                    return false;
                }
                let raw = el.text().collect::<String>();
                let t = raw.trim();
                !t.is_empty() && !t.contains("Altersfreigabe") && !t.contains("Age Rating")
            })
        })
        .map(|el| el_text(el, ""))
        .filter(|s| !s.is_empty());

    static AGE_LI_SEL: OnceLock<Selector> = OnceLock::new();
    let age_li_sel = AGE_LI_SEL.get_or_init(|| Selector::parse("ul li").unwrap());
    let age_reasons = find_dt(&doc, &["age rating", "altersfreigabe"])
        .and_then(|dt| find_next_by_tag(dt, "details"))
        .map(|d| d.select(age_li_sel).map(|li| el_text(li, " ")).collect())
        .unwrap_or_default();

    let privacy_linked = privacy_items(&doc, &["Data Linked to You", "Mit dir verknüpfte Daten"]);
    let privacy_unlinked = privacy_items(
        &doc,
        &["Data Not Linked to You", "Nicht mit dir verknüpfte Daten"],
    );
    let privacy_tracked = privacy_items(
        &doc,
        &[
            "Data Used to Track You",
            "Daten, die zum Tracking deiner Person verwendet werden",
        ],
    );

    static NC_SEL: OnceLock<Selector> = OnceLock::new();
    let nc_sel = NC_SEL.get_or_init(|| Selector::parse("h2").unwrap());
    let not_collected = doc.select(nc_sel).any(|el| {
        let raw = el.text().collect::<String>();
        let t = raw.trim();
        t == "Data Not Collected" || t == "Keine Daten erfasst"
    });
    let privacy_not_collected = if not_collected { "True" } else { "False" }.to_string();

    static VH_LI: OnceLock<Selector> = OnceLock::new();
    static VH_H: OnceLock<Selector> = OnceLock::new();
    static VH_T: OnceLock<Selector> = OnceLock::new();
    static VH_P: OnceLock<Selector> = OnceLock::new();
    static VH_RE: OnceLock<Regex> = OnceLock::new();
    let vh_li = VH_LI.get_or_init(|| Selector::parse("dialog ul li").unwrap());
    let vh_h = VH_H.get_or_init(|| Selector::parse("h3, h4, h5").unwrap());
    let vh_t = VH_T.get_or_init(|| Selector::parse("time").unwrap());
    let vh_p = VH_P.get_or_init(|| Selector::parse("p").unwrap());
    let vh_re =
        VH_RE.get_or_init(|| Regex::new(r"\b(?:Version\s*)?(\d+\.\d+(?:\.\d+)?)\b").unwrap());

    let version_history = doc
        .select(vh_li)
        .filter_map(|li| {
            let heading = li
                .select(vh_h)
                .next()
                .map(|h| el_text(h, " "))
                .unwrap_or_default();
            let time_el = li.select(vh_t).next()?;
            let date = time_el
                .value()
                .attr("datetime")
                .map(str::to_string)
                .unwrap_or_else(|| time_el.text().collect::<String>().trim().to_string());
            let version = vh_re.captures(&heading)?.get(1)?.as_str().to_string();
            let notes = li
                .select(vh_p)
                .next()
                .map(|p| el_text(p, " "))
                .filter(|s| !s.is_empty());
            Some(VersionEntry {
                version,
                date,
                notes,
            })
        })
        .collect();

    static LINK_SEL: OnceLock<Selector> = OnceLock::new();
    let link_sel = LINK_SEL.get_or_init(|| Selector::parse("a[href]").unwrap());
    let privacy_policy_link = doc
        .select(link_sel)
        .find(|el| {
            (*el)
                .children()
                .filter_map(|n| n.value().as_text())
                .any(|t| {
                    let lower = t.to_lowercase();
                    lower.contains("datenschutz") || lower.contains("privacy policy")
                })
        })
        .and_then(|el| el.value().attr("href"))
        .map(str::to_string);

    let similar_apps = extract_app_refs(&doc);

    Some(AppData {
        url: url.to_string(),
        app_name,
        developer_name: developer,
        category,
        price,
        description,
        similar_apps,
        review_count,
        review_average,
        review_one: ratings[0],
        review_two: ratings[1],
        review_three: ratings[2],
        review_four: ratings[3],
        review_five: ratings[4],
        versions,
        size,
        languages,
        age,
        age_reasons,
        privacy_linked,
        privacy_unlinked,
        privacy_tracked,
        privacy_not_collected,
        version_history,
        in_app_purchases,
        privacy_policy_link,
    })
}
