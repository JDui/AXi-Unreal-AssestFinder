use std::collections::BTreeMap;
use std::env;
use std::fs::{self, File};
use std::io::{self, BufReader, Read};
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use std::thread;
use std::time::Instant;

const BUFFER_SIZE: usize = 1024 * 1024;

#[derive(Clone)]
struct FileItem {
    path: PathBuf,
    size: u64,
}

fn is_asset(path: &Path) -> bool {
    matches!(
        path.extension()
            .and_then(|value| value.to_str())
            .map(|value| value.to_ascii_lowercase())
            .as_deref(),
        Some("uasset" | "umap" | "uexp" | "ubulk")
    )
}

fn collect_files(root: &Path) -> io::Result<BTreeMap<String, FileItem>> {
    let mut result = BTreeMap::new();
    let mut pending = vec![root.to_path_buf()];
    while let Some(directory) = pending.pop() {
        for entry in fs::read_dir(directory)? {
            let entry = entry?;
            let path = entry.path();
            let file_type = entry.file_type()?;
            if file_type.is_dir() {
                pending.push(path);
            } else if file_type.is_file() && is_asset(&path) {
                let relative = path
                    .strip_prefix(root)
                    .expect("collected path must remain below root")
                    .to_string_lossy()
                    .replace('\\', "/");
                let key = relative.to_lowercase();
                if result
                    .insert(
                        key,
                        FileItem {
                            path,
                            size: entry.metadata()?.len(),
                        },
                    )
                    .is_some()
                {
                    return Err(io::Error::new(
                        io::ErrorKind::InvalidData,
                        format!("case-insensitive duplicate path: {relative}"),
                    ));
                }
            }
        }
    }
    Ok(result)
}

fn files_equal(left: &Path, right: &Path) -> io::Result<bool> {
    let mut left_reader = BufReader::with_capacity(BUFFER_SIZE, File::open(left)?);
    let mut right_reader = BufReader::with_capacity(BUFFER_SIZE, File::open(right)?);
    let mut left_buffer = vec![0_u8; BUFFER_SIZE];
    let mut right_buffer = vec![0_u8; BUFFER_SIZE];
    loop {
        let left_size = left_reader.read(&mut left_buffer)?;
        let right_size = right_reader.read(&mut right_buffer)?;
        if left_size != right_size {
            return Ok(false);
        }
        if left_size == 0 {
            return Ok(true);
        }
        if left_buffer[..left_size] != right_buffer[..right_size] {
            return Ok(false);
        }
    }
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let arguments: Vec<String> = env::args().collect();
    if arguments.len() != 3 {
        eprintln!("usage: ue_asset_diff_probe <old-folder> <new-folder>");
        std::process::exit(2);
    }
    let started_at = Instant::now();
    let old_root = Path::new(&arguments[1]).canonicalize()?;
    let new_root = Path::new(&arguments[2]).canonicalize()?;
    let old_files = collect_files(&old_root)?;
    let new_files = collect_files(&new_root)?;

    let mut added = 0_usize;
    let mut deleted = 0_usize;
    let mut modified = 0_usize;
    let mut pairs = Vec::new();
    for (key, old_item) in &old_files {
        match new_files.get(key) {
            None => deleted += 1,
            Some(new_item) if old_item.size != new_item.size => modified += 1,
            Some(new_item) => pairs.push((old_item.path.clone(), new_item.path.clone())),
        }
    }
    for key in new_files.keys() {
        if !old_files.contains_key(key) {
            added += 1;
        }
    }

    let workers = thread::available_parallelism()
        .map(|count| count.get())
        .unwrap_or(1)
        .min(8);
    let queue = Arc::new(Mutex::new(pairs));
    let mut handles = Vec::with_capacity(workers);
    for _ in 0..workers {
        let queue = Arc::clone(&queue);
        handles.push(thread::spawn(move || -> io::Result<(usize, usize)> {
            let mut unchanged = 0;
            let mut changed = 0;
            loop {
                let pair = queue.lock().expect("comparison queue poisoned").pop();
                let Some((old_path, new_path)) = pair else {
                    break;
                };
                if files_equal(&old_path, &new_path)? {
                    unchanged += 1;
                } else {
                    changed += 1;
                }
            }
            Ok((unchanged, changed))
        }));
    }

    let mut unchanged = 0_usize;
    for handle in handles {
        let (thread_unchanged, thread_modified) =
            handle.join().map_err(|_| "comparison worker panicked")??;
        unchanged += thread_unchanged;
        modified += thread_modified;
    }

    println!(
        "{{\"added\":{added},\"modified\":{modified},\"deleted\":{deleted},\
         \"unchanged\":{unchanged},\"old_files\":{},\"new_files\":{},\
         \"elapsed_seconds\":{:.6}}}",
        old_files.len(),
        new_files.len(),
        started_at.elapsed().as_secs_f64()
    );
    Ok(())
}
