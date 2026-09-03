use super::types::*;
use std::collections::HashSet;
use std::fs;
use std::path::Path;

/// references.
pub fn locate_callsites(root_dir: &str, config: &ScanConfig) -> ScanResult {
    let mut result = ScanResult::default();
    let ext_set: HashSet<&str> = config.extensions.iter().map(|s| s.as_str()).collect();

    walk_dir(Path::new(root_dir), &ext_set, &mut |path| {
        let content = match fs::read_to_string(path) {
            Ok(c) => c,
            Err(_) => return,
        };
        let file_path = path.to_string_lossy().to_string();
        let hits = locate_callsites_in_source(&file_path, &content, config);
        result.files_scanned += 1;
        if !hits.is_empty() {
            result.files_with_hits += 1;
            result.callsites.extend(hits);
        }
    });

    result
}

/// Scan a single source string for callsites. This is the core matching
/// engine, factored out so it can be tested without filesystem access.
pub fn locate_callsites_in_source(
    file_path: &str,
    source: &str,
    config: &ScanConfig,
) -> Vec<Callsite> {
    let mut hits = Vec::new();

    for (line_idx, line) in source.lines().enumerate() {
        let line_number = line_idx + 1;
        let trimmed = line.trim();

        for sdk in &config.sdk_names {
            if is_import_line(trimmed, sdk) {
                hits.push(Callsite {
                    file_path: file_path.to_string(),
                    line_number,
                    column: line.find(sdk.as_str()).unwrap_or(0) + 1,
                    line_content: line.to_string(),
                    kind: CallsiteKind::Import,
                    matched_pattern: sdk.clone(),
                });
            }
        }

        for pattern in &config.method_patterns {
            if let Some(col) = line.find(pattern.as_str()) {
                // Skip if inside a comment.
                if is_comment(trimmed) {
                    continue;
                }
                hits.push(Callsite {
                    file_path: file_path.to_string(),
                    line_number,
                    column: col + 1,
                    line_content: line.to_string(),
                    kind: CallsiteKind::MethodCall,
                    matched_pattern: pattern.clone(),
                });
            }
        }

        for url in &config.api_base_urls {
            if let Some(col) = line.find(url.as_str()) {
                hits.push(Callsite {
                    file_path: file_path.to_string(),
                    line_number,
                    column: col + 1,
                    line_content: line.to_string(),
                    kind: CallsiteKind::UrlReference,
                    matched_pattern: url.clone(),
                });
            }
        }

        for sdk in &config.sdk_names {
            let type_prefix = capitalize_first(sdk);
            if trimmed.contains(&type_prefix) && !is_import_line(trimmed, sdk) {
                if is_comment(trimmed) {
                    continue;
                }
                if let Some(col) = line.find(&type_prefix) {
                    hits.push(Callsite {
                        file_path: file_path.to_string(),
                        line_number,
                        column: col + 1,
                        line_content: line.to_string(),
                        kind: CallsiteKind::TypeReference,
                        matched_pattern: type_prefix.clone(),
                    });
                }
            }
        }
    }

    hits
}

/// Check if a line is an import/require statement referencing the given package.
fn is_import_line(line: &str, package: &str) -> bool {
    // JS/TS: import ... from 'package'  or  require('package')
    // Python: import package  or  from package import ...
    let patterns = [
        format!("from '{package}'"),
        format!("from \"{package}\""),
        format!("require('{package}'"),
        format!("require(\"{package}\""),
        format!("import {package}"),
        format!("from {package} import"),
        format!("from {package}."),
    ];
    patterns.iter().any(|p| line.contains(p.as_str()))
}

fn is_comment(line: &str) -> bool {
    line.starts_with("//")
        || line.starts_with('#')
        || line.starts_with("/*")
        || line.starts_with('*')
}

fn capitalize_first(s: &str) -> String {
    // "stripe" → "Stripe", "@stripe/stripe-node" → "Stripe"
    let base = s
        .rsplit('/')
        .next()
        .unwrap_or(s)
        .trim_start_matches('@')
        .split('-')
        .next()
        .unwrap_or(s);
    let mut chars = base.chars();
    match chars.next() {
        None => String::new(),
        Some(c) => c.to_uppercase().to_string() + chars.as_str(),
    }
}

// Directories to skip during recursive walk.
const SKIP_DIRS: &[&str] = &[
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "target",
    "build",
    "dist",
    ".next",
    ".compart",
    "vendor",
    ".mypy_cache",
    ".pytest_cache",
];

fn walk_dir(dir: &Path, extensions: &HashSet<&str>, visit: &mut impl FnMut(&Path)) {
    let Ok(entries) = fs::read_dir(dir) else {
        return;
    };
    for entry in entries.flatten() {
        let path = entry.path();
        let name = entry.file_name().to_string_lossy().to_string();

        if path.is_dir() {
            if SKIP_DIRS.contains(&name.as_str()) {
                continue;
            }
            walk_dir(&path, extensions, visit);
        } else if path.is_file() {
            if let Some(ext) = path.extension().and_then(|e| e.to_str()) {
                if extensions.contains(ext) {
                    visit(&path);
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn stripe_config() -> ScanConfig {
        ScanConfig {
            sdk_names: vec!["stripe".into()],
            api_base_urls: vec!["api.stripe.com".into()],
            method_patterns: vec![
                "charges.create".into(),
                "charges.retrieve".into(),
                "refunds.create".into(),
            ],
            extensions: default_extensions(),
        }
    }

    #[test]
    fn ast_detects_js_import() {
        let source = r#"
import Stripe from 'stripe';
const stripe = new Stripe(process.env.STRIPE_KEY);
"#;
        let hits = locate_callsites_in_source("app.ts", source, &stripe_config());
        assert!(
            hits.iter().any(|c| c.kind == CallsiteKind::Import),
            "should detect import statement"
        );
    }

    #[test]
    fn ast_detects_require_import() {
        let source = r#"const stripe = require('stripe')('sk_test_xxx');"#;
        let hits = locate_callsites_in_source("app.js", source, &stripe_config());
        assert!(hits.iter().any(|c| c.kind == CallsiteKind::Import));
    }

    #[test]
    fn ast_detects_python_import() {
        let source = r#"
import stripe
stripe.api_key = "sk_test_xxx"
charge = stripe.charges.create(amount=100, currency="usd")
"#;
        let hits = locate_callsites_in_source("payments.py", source, &stripe_config());
        assert!(hits.iter().any(|c| c.kind == CallsiteKind::Import));
        assert!(hits.iter().any(|c| c.kind == CallsiteKind::MethodCall));
    }

    #[test]
    fn ast_detects_method_call() {
        let source = r#"
const charge = await stripe.charges.create({ amount: 2000, currency: 'usd' });
const existing = await stripe.charges.retrieve('ch_123');
"#;
        let hits = locate_callsites_in_source("billing.ts", source, &stripe_config());
        let method_calls: Vec<_> = hits
            .iter()
            .filter(|c| c.kind == CallsiteKind::MethodCall)
            .collect();
        assert_eq!(method_calls.len(), 2, "should find 2 method calls");
    }

    #[test]
    fn ast_detects_url_reference() {
        let source = r#"
const resp = await fetch('https://api.stripe.com/v1/charges', {
  headers: { Authorization: `Bearer ${key}` },
});
"#;
        let hits = locate_callsites_in_source("raw_api.ts", source, &stripe_config());
        assert!(hits.iter().any(|c| c.kind == CallsiteKind::UrlReference));
    }

    #[test]
    fn ast_skips_comments() {
        let source = r#"
// stripe.charges.create is the old way
/* stripe.refunds.create should not match either */
const real = stripe.charges.create({ amount: 100 });
"#;
        let hits = locate_callsites_in_source("commented.ts", source, &stripe_config());
        let method_calls: Vec<_> = hits
            .iter()
            .filter(|c| c.kind == CallsiteKind::MethodCall)
            .collect();
        assert_eq!(
            method_calls.len(),
            1,
            "should only match the real call, not comments"
        );
    }

    #[test]
    fn ast_detects_type_reference() {
        let source = r#"
import Stripe from 'stripe';
function processCharge(charge: Stripe.Charge): void {
  console.log(charge.id);
}
"#;
        let hits = locate_callsites_in_source("types.ts", source, &stripe_config());
        assert!(
            hits.iter().any(|c| c.kind == CallsiteKind::TypeReference),
            "should detect Stripe type reference"
        );
    }

    #[test]
    fn ast_empty_source_returns_nothing() {
        let hits = locate_callsites_in_source("empty.ts", "", &stripe_config());
        assert!(hits.is_empty());
    }

    #[test]
    fn ast_scan_result_affected_files() {
        let mut result = ScanResult::default();
        result.callsites.push(Callsite {
            file_path: "a.ts".into(),
            line_number: 1,
            column: 1,
            line_content: "x".into(),
            kind: CallsiteKind::Import,
            matched_pattern: "stripe".into(),
        });
        result.callsites.push(Callsite {
            file_path: "b.ts".into(),
            line_number: 5,
            column: 1,
            line_content: "y".into(),
            kind: CallsiteKind::MethodCall,
            matched_pattern: "charges.create".into(),
        });
        result.callsites.push(Callsite {
            file_path: "a.ts".into(),
            line_number: 10,
            column: 1,
            line_content: "z".into(),
            kind: CallsiteKind::MethodCall,
            matched_pattern: "charges.retrieve".into(),
        });
        let files = result.affected_files();
        assert_eq!(files, vec!["a.ts", "b.ts"]);
    }

    #[test]
    fn ast_locate_callsites_in_temp_dir() {
        let dir = std::env::temp_dir().join(format!(
            "compart_ast_test_{}",
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        fs::create_dir_all(&dir).unwrap();
        let file = dir.join("service.ts");
        fs::write(
            &file,
            r#"
import Stripe from 'stripe';
const stripe = new Stripe(key);
const charge = await stripe.charges.create({ amount: 500 });
"#,
        )
        .unwrap();

        let result = locate_callsites(dir.to_str().unwrap(), &stripe_config());
        assert_eq!(result.files_scanned, 1);
        assert_eq!(result.files_with_hits, 1);
        assert!(
            result.callsites.len() >= 2,
            "should find import + method call"
        );

        let _ = fs::remove_dir_all(&dir);
    }

    fn default_extensions() -> Vec<String> {
        vec!["ts".into(), "js".into(), "py".into()]
    }
}
