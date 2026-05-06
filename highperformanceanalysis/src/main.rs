use highperformanceanalysis::{parser, utils::reconstruct_url};
use rayon::prelude::*;
use regex::Regex;
use std::path::Path;
use std::sync::{atomic::{AtomicU64, Ordering}, Mutex};
use std::time::Instant;

const COLUMNS: &[&str] = &[
    "url", "app_name", "developer_name", "category", "price", "description",
    "review_count", "review_average",
    "review_one", "review_two", "review_three", "review_four", "review_five",
    "versions", "size", "languages",
    "age", "age_reasons",
    "privacy_linked", "privacy_unlinked", "privacy_tracked", "privacy_not_collected",
    "version_history", "in_app_purchases", "privacy_policy_link", "similar_apps",
];

fn to_row(data: &parser::AppData) -> Vec<String> {
    vec![
        data.url.clone(),
        data.app_name.clone().unwrap_or_default(),
        data.developer_name.clone().unwrap_or_default(),
        data.category.clone().unwrap_or_default(),
        data.price.clone().unwrap_or_default(),
        data.description.clone().unwrap_or_default(),
        data.review_count.clone().unwrap_or_default(),
        data.review_average.clone().unwrap_or_default(),
        data.review_one.map(|v| v.to_string()).unwrap_or_default(),
        data.review_two.map(|v| v.to_string()).unwrap_or_default(),
        data.review_three.map(|v| v.to_string()).unwrap_or_default(),
        data.review_four.map(|v| v.to_string()).unwrap_or_default(),
        data.review_five.map(|v| v.to_string()).unwrap_or_default(),
        data.versions.clone().unwrap_or_default(),
        data.size.map(|v| v.to_string()).unwrap_or_default(),
        data.languages.clone().unwrap_or_default(),
        data.age.clone().unwrap_or_default(),
        serde_json::to_string(&data.age_reasons).unwrap_or_default(),
        serde_json::to_string(&data.privacy_linked).unwrap_or_default(),
        serde_json::to_string(&data.privacy_unlinked).unwrap_or_default(),
        serde_json::to_string(&data.privacy_tracked).unwrap_or_default(),
        data.privacy_not_collected.clone(),
        serde_json::to_string(&data.version_history).unwrap_or_default(),
        data.in_app_purchases.clone().unwrap_or_default(),
        data.privacy_policy_link.clone().unwrap_or_default(),
        serde_json::to_string(&data.similar_apps).unwrap_or_default(),
    ]
}

fn run_single(path: &str, url_arg: Option<&String>) {
    let url = url_arg
        .map(|s| s.clone())
        .or_else(|| reconstruct_url(path))
        .unwrap_or_else(|| "unknown".to_string());
    let html = std::fs::read_to_string(path).expect("could not read file");
    match parser::extract_app_data(&url, &html) {
        Some(data) => println!("{}", serde_json::to_string_pretty(&data).unwrap()),
        None => eprintln!("No app data found (missing JSON-LD script tag?)"),
    }
}

fn run_directory(dir: &str, regex_arg: Option<&String>, output_arg: Option<&String>) {
    let filter: Option<Regex> = regex_arg
        .filter(|s| !s.is_empty())
        .map(|p| Regex::new(p).expect("invalid regex"));
    let output_path = output_arg.map(|s| s.as_str()).unwrap_or("parsed.csv");

    let writer = Mutex::new(csv::Writer::from_path(output_path).expect("could not open output file"));
    writer.lock().unwrap().write_record(COLUMNS).unwrap();

    let count = AtomicU64::new(0);
    let skipped = AtomicU64::new(0);
    let start = Instant::now();

    let entries: Vec<_> = walkdir::WalkDir::new(dir)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file())
        .collect();

    entries.par_iter().for_each(|entry| {
        let filename = entry.file_name().to_string_lossy();

        if let Some(re) = &filter {
            if !re.is_match(&filename) {
                skipped.fetch_add(1, Ordering::Relaxed);
                return;
            }
        }

        let path = entry.path();
        let url = reconstruct_url(&filename)
            .unwrap_or_else(|| path.to_string_lossy().to_string());

        let html = match std::fs::read_to_string(path) {
            Ok(h) => h,
            Err(_) => { skipped.fetch_add(1, Ordering::Relaxed); return; }
        };

        match parser::extract_app_data(&url, &html) {
            Some(data) => {
                writer.lock().unwrap().write_record(&to_row(&data)).unwrap();
                let n = count.fetch_add(1, Ordering::Relaxed) + 1;
                if n % 10_000 == 0 {
                    let elapsed = start.elapsed().as_secs_f64();
                    eprintln!(
                        "  {:>10} parsed | {:>10} skipped | {:>8.1} files/s | {:.1}h elapsed",
                        n, skipped.load(Ordering::Relaxed), n as f64 / elapsed, elapsed / 3600.0
                    );
                }
            }
            None => { skipped.fetch_add(1, Ordering::Relaxed); }
        }
    });

    writer.lock().unwrap().flush().unwrap();
    let elapsed = start.elapsed().as_secs_f64();
    eprintln!("Done: {} apps -> {} ({:.1}h total)",
        count.load(Ordering::Relaxed), output_path, elapsed / 3600.0);
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let path = args.get(1).unwrap_or_else(|| {
        eprintln!("Usage:");
        eprintln!("  highperformanceanalysis <file> [url]");
        eprintln!("  highperformanceanalysis <dir>  [regex] [output.csv]");
        std::process::exit(1);
    });

    if Path::new(path).is_dir() {
        run_directory(path, args.get(2), args.get(3));
    } else {
        run_single(path, args.get(2));
    }
}
