#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python-only adapter to apply publication "stream" and create project structure.
Default project location: C:\Projects\GidroMeteo (Windows) or /opt/hydrometeo (Unix).
"""

import argparse
import datetime
import logging
import os
import re
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class FileEntry(NamedTuple):
    """Represents a parsed file entry."""
    path: str
    content: str


class ParseError(NamedTuple):
    """Represents a file parsing error."""
    line_number: int
    original_line: str
    parsed_path: str
    reason: str


class StreamParser:
    """Parser for file stream format."""
    
    FILE_HEADER_RE = re.compile(
        r'^\s*(?:[-—–]{0,3}\s*)?(?:BEGIN\s+FILE:|FILE:)\s*([^\s].*?)\s*(?:[-—–]{2,}.*?)?\s*$',
        re.IGNORECASE
    )
    FILE_END_RE = re.compile(r'^\s*END\s+FILE\s*$', re.IGNORECASE)
    
    # Windows reserved names
    RESERVED_NAMES = {
        'CON', 'PRN', 'AUX', 'NUL',
        'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9',
        'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
    }
    
    INVALID_CHARS = '<>"|?*'
    
    # Code block markers to skip
    CODE_MARKERS = {
        '```', '~~~', 'copy', 'edit', 'ts', 'tsx', 'js', 'jsx', 'json',
        'bash', 'sh', 'powershell', 'ps1', 'yaml', 'yml', 'dockerfile',
        'sql', 'md', 'txt'
    }

    @staticmethod
    def normalize_path(path: str) -> str:
        """Normalize and clean file path."""
        path = path.strip().strip('"').strip("'")
        # Remove trailing comments/decorators
        path = re.sub(r'\s*(?:[-—–]{2,}.*|#+.*)+$', '', path)
        # Normalize path separators
        path = path.replace('\\', '/').lstrip('./')
        return path

    @classmethod
    def validate_path(cls, path: str) -> Tuple[bool, str]:
        """Validate file path for safety and OS compatibility."""
        if not path or not path.strip():
            return False, "пустой путь"
        
        # Check for invalid characters
        for char in cls.INVALID_CHARS:
            if char in path:
                return False, f"недопустимый символ '{char}'"
        
        # Check path components
        parts = path.split('/')
        for part in parts:
            if not part:  # Empty part (double slash)
                continue
                
            # Check reserved names
            if part.upper() in cls.RESERVED_NAMES:
                return False, f"зарезервированное имя '{part}'"
            
            # Check trailing dots/spaces
            if part.endswith('.') or part.endswith(' '):
                return False, f"часть пути '{part}' оканчивается точкой/пробелом"
        
        # Check for regex artifacts
        if re.search(r'[|\\]FILE:', path) or '\\s' in path or '.+?' in path:
            return False, "остатки regex"
        
        return True, ""

    @classmethod
    def sanitize_content(cls, lines: List[str]) -> str:
        """Remove empty lines from start and end, preserve content."""
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        
        content = '\n'.join(lines)
        return content + '\n' if content else ''

    def parse(self, text: str) -> Tuple[List[FileEntry], List[ParseError]]:
        """Parse stream text into file entries and errors."""
        files: List[FileEntry] = []
        errors: List[ParseError] = []
        
        current_path: Optional[str] = None
        current_lines: List[str] = []
        
        def flush_current():
            """Save current file if valid."""
            nonlocal current_path, current_lines
            if current_path is not None:
                content = self.sanitize_content(current_lines)
                files.append(FileEntry(current_path, content))
            current_path = None
            current_lines = []

        for line_num, raw_line in enumerate(text.splitlines(), 1):
            line = raw_line.rstrip('\r\n')
            
            # Check for file header
            header_match = self.FILE_HEADER_RE.match(line)
            if header_match:
                flush_current()
                
                raw_path = header_match.group(1)
                normalized_path = self.normalize_path(raw_path)
                is_valid, error_reason = self.validate_path(normalized_path)
                
                if not is_valid:
                    errors.append(ParseError(
                        line_number=line_num,
                        original_line=line.strip(),
                        parsed_path=normalized_path,
                        reason=error_reason
                    ))
                    continue
                
                current_path = normalized_path
                current_lines = []
                continue
            
            # Check for file end
            if current_path and self.FILE_END_RE.match(line):
                flush_current()
                continue
            
            # Collect file content
            if current_path is not None:
                stripped = line.strip().lower()
                
                # Skip code block markers
                if (stripped.startswith(('```', '~~~')) or 
                    stripped in self.CODE_MARKERS):
                    continue
                
                current_lines.append(line)
        
        # Flush final file
        flush_current()
        
        return files, errors


class FileWriter:
    """Handles writing files to filesystem."""
    
    def __init__(self, root_dir: str, encoding: str = 'utf-8', 
                 eol: str = 'crlf', backup: bool = False):
        self.root_path = Path(root_dir).resolve()
        self.encoding = encoding
        self.eol = eol
        self.backup = backup
    
    def ensure_safe_path(self, relative_path: str) -> Path:
        """Ensure path is under root directory (prevent path traversal)."""
        full_path = (self.root_path / relative_path).resolve()
        
        try:
            full_path.relative_to(self.root_path)
        except ValueError:
            raise ValueError(f'Unsafe path traversal: {relative_path}')
        
        return full_path
    
    def normalize_line_endings(self, content: str) -> str:
        """Normalize line endings according to eol setting."""
        # First normalize to LF
        content = content.replace('\r\n', '\n').replace('\r', '\n')
        
        # Convert to target format
        if self.eol == 'crlf':
            content = content.replace('\n', '\r\n')
        
        return content
    
    def create_backup(self, file_path: Path) -> None:
        """Create backup of existing file."""
        if file_path.exists():
            timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
            backup_path = file_path.with_suffix(f'{file_path.suffix}.bak.{timestamp}')
            shutil.copy2(file_path, backup_path)
            logger.info(f'[BACKUP] {file_path} -> {backup_path}')
    
    def write_file(self, file_entry: FileEntry, dry_run: bool = False) -> bool:
        """Write single file entry to filesystem."""
        try:
            dest_path = self.ensure_safe_path(file_entry.path)
            
            # Create parent directories
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Normalize content
            content = self.normalize_line_endings(file_entry.content)
            
            if dry_run:
                logger.info(f'[DRY] {dest_path} ({len(content)} bytes)')
                return True
            
            # Create backup if needed
            if self.backup:
                self.create_backup(dest_path)
            
            # Write file
            dest_path.write_text(content, encoding=self.encoding, newline='')
            logger.info(f'[WROTE] {dest_path}')
            return True
            
        except (ValueError, OSError) as e:
            logger.error(f'[ERROR] {file_entry.path}: {e}')
            return False
    
    def write_files(self, files: List[FileEntry], 
                   dry_run: bool = False) -> Tuple[int, int]:
        """Write multiple files, return (success_count, failure_count)."""
        success_count = 0
        failure_count = 0
        
        for file_entry in files:
            if self.write_file(file_entry, dry_run):
                success_count += 1
            else:
                failure_count += 1
        
        return success_count, failure_count


class ZipBuilder:
    """Handles ZIP archive creation."""
    
    @staticmethod
    def create_zip(zip_path: str, root_dir: str, top_name: str = 'GidroMeteo') -> bool:
        """Create ZIP archive from directory."""
        try:
            root_path = Path(root_dir)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for file_path in root_path.rglob('*'):
                    if file_path.is_file():
                        relative_path = file_path.relative_to(root_path)
                        archive_path = f"{top_name}/{relative_path.as_posix()}"
                        zip_file.write(file_path, archive_path)
            
            logger.info(f'[ZIP] {zip_path}')
            return True
            
        except Exception as e:
            logger.error(f'[ERROR] ZIP: {e}')
            return False


def get_default_root() -> str:
    """Get default project root based on OS."""
    if os.name == 'nt':  # Windows
        return r"C:\Projects\GidroMeteo"
    return "/opt/hydrometeo"


def read_input(input_path: str) -> str:
    """Read input from file or stdin."""
    if input_path == '-':
        return sys.stdin.read()
    
    input_file = Path(input_path)
    if not input_file.exists():
        raise FileNotFoundError(f'Input file not found: {input_path}')
    
    return input_file.read_text(encoding='utf-8-sig')


def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(
        description='Apply HydroMeteo publication stream to files'
    )
    parser.add_argument(
        '--input', 
        help='Path to stream file or "-" for STDIN', 
        default='-'
    )
    parser.add_argument(
        '--root', 
        help='Project root (default: C:\\Projects\\GidroMeteo on Windows)', 
        default=None
    )
    parser.add_argument('--encoding', default='utf-8')
    parser.add_argument('--eol', choices=['lf', 'crlf'], default='crlf')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--backup', action='store_true')
    parser.add_argument('--quiet', action='store_true')
    parser.add_argument('--zip-out')
    parser.add_argument('--zip-topname', default='GidroMeteo')
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.quiet:
        logger.setLevel(logging.ERROR)
    
    # Determine root directory
    root_dir = args.root or get_default_root()
    
    try:
        # Create root directory if needed
        root_path = Path(root_dir)
        if not root_path.exists():
            root_path.mkdir(parents=True, exist_ok=True)
            logger.info(f'[+] Created project root: {root_dir}')
        
        # Read input
        text = read_input(args.input)
        
        # Parse stream
        stream_parser = StreamParser()
        files, errors = stream_parser.parse(text)
        
        # Report parsing results
        if not args.quiet:
            logger.info(f'Files parsed: {len(files)}')
            for file_entry in files:
                print(f'  - {file_entry.path}')
            
            if errors:
                logger.warning(f'Invalid file headers: {len(errors)}')
                for error in errors:
                    print(f'  line {error.line_number}: {error.original_line} -> '
                          f'{error.parsed_path} ({error.reason})')
        
        if not files:
            logger.error('No FILE blocks found.')
            return 3
        
        # Write files
        file_writer = FileWriter(
            root_dir=root_dir,
            encoding=args.encoding,
            eol=args.eol,
            backup=args.backup
        )
        
        success_count, failure_count = file_writer.write_files(files, args.dry_run)
        
        if not args.quiet:
            logger.info(f'Written: {success_count}, failed: {failure_count}, '
                       f'invalid: {len(errors)}')
        
        # Create ZIP if requested
        if args.zip_out and not args.dry_run:
            ZipBuilder.create_zip(args.zip_out, root_dir, args.zip_topname)
        
        return 0
        
    except Exception as e:
        logger.error(f'Fatal error: {e}')
        return 1


if __name__ == '__main__':
    sys.exit(main())