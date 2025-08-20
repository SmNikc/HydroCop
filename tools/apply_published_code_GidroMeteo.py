#!/usr/bin/env python3

-- coding: utf-8 --
Python-only comments
Adapter to apply the publication "stream" and create C:\Projects\GidroMeteo by default on Windows.

import argparse
import os
import re
import sys
import shutil
import datetime
import zipfile
from typing import List, Tuple, Dict

FILE_HEADER_RE = re.compile(
r'^\s*(?:[-–—]{0,3}\s*)?(?:BEGIN\s+FILE:|FILE:)\s*([^\s].?)\s(?:[-–—]{2,}.?)?\s$',
re.IGNORECASE
)
FILE_END_RE = re.compile(r'^\sEND\s+FILE\s$', re.IGNORECASE)

def normalize_relpath(rel: str) -> str:
rel = rel.strip().strip('"').strip("'")
rel = re.sub(r'\s*(?:[-–—]{2,}.*|)+)$', '', rel)
rel = rel.replace('\', '/').lstrip('./')
return rel

def sanitize(lines: List[str]) -> str:
while lines and not lines[0].strip(): lines.pop(0)
while lines and not lines[-1].strip(): lines.pop()
return '\n'.join(lines) + ('\n' if lines else '')

def ensure_under_root(root: str, rel: str) -> str:
root_abs = os.path.abspath(root)
dest = os.path.abspath(os.path.join(root, rel))
if not dest.startswith(root_abs):
raise ValueError(f'Unsafe path traversal: {rel}')
return dest

def is_valid_path(path: str) -> Tuple[bool, str]:
if not path or path.strip() == '': return False, "пустой путь"
invalid_chars = '<>"|?'
for ch in invalid_chars:
if ch in path: return False, f"недопустимый символ '{ch}'"
invalid_names = {'CON','PRN','AUX','NUL','COM1','COM2','COM3','COM4','COM5','COM6','COM7','COM8','COM9','LPT1','LPT2','LPT3','LPT4','LPT5','LPT6','LPT7','LPT8','LPT9'}
parts = path.split('/')
for part in parts:
if part.upper() in invalid_names: return False, f"зарезервированное имя '{part}'"
if part.endswith('.') or part.endswith(' '): return False, f"часть пути '{part}' оканчивается точкой/пробелом"
if re.search(r'[|\]FILE:', path) or '\s' in path or '.+?' in path: return False, "остатки regex"
return True, ""

def parse_stream(text: str):
files: List[Tuple[str, str]] = []
invalid_files: List[Dict[str, str]] = []
current = None
buf: List[str] = []
def flush():
nonlocal current, buf, files
if current is not None:
files.append((current, sanitize(buf)))
current, buf = None, []
for line_num, raw in enumerate(text.splitlines(), 1):
line = raw.rstrip('\r\n')
m = FILE_HEADER_RE.match(line)
if m:
flush()
rel = normalize_relpath(m.group(1))
ok, reason = is_valid_path(rel)
if not ok:
invalid_files.append({'line': str(line_num), 'original_line': line.strip(), 'parsed_path': rel, 'reason': reason})
current = None
continue
current = rel
buf = []
continue
if current and FILE_END_RE.match(line):
flush(); continue
if current is not None:
stripped = line.strip().lower()
if (stripped.startswith("```") or stripped.startswith("~~~") or
stripped in {"copy","edit","ts","tsx","js","jsx","json","bash","sh","powershell","ps1","yaml","yml","dockerfile","sql","md","txt"}):
continue
buf.append(line)
flush()
return files, invalid_files

def write_files(files, root, eol='crlf', encoding='utf-8', dry_run=False, backup=False, verbose=True):
count = 0
failed = []
for rel, content in files:
try:
dest = ensure_under_root(root, rel)
dir_path = os.path.dirname(dest)
if dir_path: os.makedirs(dir_path, exist_ok=True)
data = content.replace('\r\n','\n').replace('\r','\n')
if eol == 'crlf': data = data.replace('\n','\r\n')
if dry_run:
if verbose: print(f'[DRY] {dest} ({len(data)} bytes)')
count += 1; continue
if backup and os.path.exists(dest):
ts = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
shutil.copy2(dest, dest + f'.bak.{ts}')
if verbose: print(f'[BACKUP] {dest} -> {dest}.bak.{ts}')
with open(dest, 'w', encoding=encoding, newline='') as f:
f.write(data)
count += 1
if verbose: print(f'[WROTE] {dest}')
except (ValueError, OSError) as e:
failed.append({'path': rel, 'error': str(e)})
if verbose: print(f'[ERROR] {rel}: {e}')
return count, failed

def build_zip(zip_out, topname, root):
if not zip_out: return
try:
with zipfile.ZipFile(zip_out, 'w', zipfile.ZIP_DEFLATED) as z:
base = os.path.abspath(root)
for dp, _, fns in os.walk(root):
for fn in fns:
p = os.path.join(dp, fn)
rel = os.path.relpath(p, base).replace('\','/')
z.write(p, f"{topname}/{rel}")
print(f"[ZIP] {zip_out}")
except Exception as e:
print(f"[ERROR] ZIP: {e}")

def default_root() -> str:
if os.name == 'nt':
return r"C:\Projects\GidroMeteo"
return "/opt/hydrometeo"

def main():
ap = argparse.ArgumentParser(description='Apply HydroMeteo publication stream to files')
ap.add_argument('--input', help='Path to stream file or "-" for STDIN', default='-')
ap.add_argument('--root', help='Project root (default: C:\Projects\GidroMeteo on Windows)', default=None)
ap.add_argument('--encoding', default='utf-8')
ap.add_argument('--eol', choices=['lf','crlf'], default='crlf')
ap.add_argument('--dry-run', action='store_true')
ap.add_argument('--backup', action='store_true')
ap.add_argument('--quiet', action='store_true')
ap.add_argument('--zip-out')
ap.add_argument('--zip-topname', default='GidroMeteo')
args = ap.parse_args()

root = args.root or default_root()
if not os.path.exists(root):
    os.makedirs(root, exist_ok=True)
    if not args.quiet: print(f"[+] Created project root: {root}")

if args.input == '-':
    text = sys.stdin.read()
else:
    if not os.path.exists(args.input):
        print(f'Input not found: {args.input}', file=sys.stderr); sys.exit(2)
    with open(args.input, 'r', encoding='utf-8-sig') as fh:
        text = fh.read()

files, invalid = parse_stream(text)
if not args.quiet:
    print(f'Files parsed: {len(files)}')
    for rel,_ in files: print(f'  - {rel}')
if invalid and not args.quiet:
    print(f'Invalid file headers: {len(invalid)}')
    for it in invalid:
        print(f'  line {it["line"]}: {it["original_line"]} -> {it["parsed_path"]} ({it["reason"]})')

if not files:
    print('No FILE blocks found.', file=sys.stderr); sys.exit(3)

n, failed = write_files(files, root, eol=args.eol, encoding=args.encoding,
                        dry_run=args.dry_run, backup=args.backup, verbose=not args.quiet)
if not args.quiet:
    print(f'Written: {n}, failed: {len(failed)}, invalid: {len(invalid)}')
if args.zip_out and not args.dry_run:
    build_zip(args.zip_out, args.zip_topname, root)


if name == 'main':
main()
