"""
System Tools - SerpentAI System Operation Tools
Enables computer control capabilities
"""

import os
import sys
import subprocess
import shutil
import platform
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_WORKDIR = str(Path.home())


def _get_workdir(workdir: Optional[str] = None) -> str:
    if workdir:
        path = Path(workdir).expanduser().resolve()
        if path.exists() and path.is_dir():
            return str(path)
    return DEFAULT_WORKDIR


def fs_list_directory(args: Dict) -> Dict:
    path = args.get("path", ".")
    show_hidden = args.get("show_hidden", False)
    try:
        target = Path(path).expanduser().resolve()
        if not target.exists():
            return {"error": f"Path does not exist: {path}", "success": False}
        if not target.is_dir():
            return {"error": f"Not a directory: {path}", "success": False}
        items = []
        for item in sorted(target.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            if not show_hidden and item.name.startswith("."):
                continue
            stat = item.stat()
            items.append({
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "size": stat.st_size if item.is_file() else None,
                "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
            })
        return {"path": str(target), "items": items, "count": len(items), "success": True}
    except Exception as e:
        return {"error": str(e), "success": False}


def fs_read_file(args: Dict) -> Dict:
    path = args.get("path")
    lines = args.get("lines")
    encoding = args.get("encoding", "utf-8")
    if not path:
        return {"error": "Missing required argument: path", "success": False}
    try:
        target = Path(path).expanduser().resolve()
        if not target.exists():
            return {"error": f"File does not exist: {path}", "success": False}
        if not target.is_file():
            return {"error": f"Not a file: {path}", "success": False}
        size = target.stat().st_size
        max_size = 10 * 1024 * 1024
        if size > max_size:
            return {"error": "File too large", "success": False}
        with open(target, "r", encoding=encoding) as f:
            if lines:
                content = "".join(f.readline() for _ in range(lines))
            else:
                content = f.read()
        return {"path": str(target), "content": content, "size": size, "success": True}
    except UnicodeDecodeError:
        return {"error": "Cannot read binary file", "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}


def fs_write_file(args: Dict) -> Dict:
    path = args.get("path")
    content = args.get("content", "")
    mode = args.get("mode", "write")
    encoding = args.get("encoding", "utf-8")
    if not path:
        return {"error": "Missing required argument: path", "success": False}
    try:
        target = Path(path).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        write_mode = "a" if mode == "append" else "w"
        with open(target, write_mode, encoding=encoding) as f:
            f.write(content)
        return {"path": str(target), "size": len(content.encode(encoding)), "success": True}
    except Exception as e:
        return {"error": str(e), "success": False}


def fs_delete(args: Dict) -> Dict:
    path = args.get("path")
    force = args.get("force", False)
    if not path:
        return {"error": "Missing required argument: path", "success": False}
    try:
        target = Path(path).expanduser().resolve()
        if not target.exists():
            return {"error": f"Path does not exist: {path}", "success": False}
        if target.is_file():
            target.unlink()
            return {"path": str(target), "type": "file", "success": True}
        elif target.is_dir():
            if not force and any(target.iterdir()):
                return {"error": "Directory not empty. Use force=true", "success": False}
            shutil.rmtree(target)
            return {"path": str(target), "type": "directory", "success": True}
        return {"error": "Unknown file type", "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}


def fs_copy(args: Dict) -> Dict:
    source = args.get("source")
    destination = args.get("destination")
    if not source or not destination:
        return {"error": "Missing required arguments", "success": False}
    try:
        src = Path(source).expanduser().resolve()
        dst = Path(destination).expanduser().resolve()
        if not src.exists():
            return {"error": "Source does not exist", "success": False}
        if src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        else:
            shutil.copytree(src, dst)
        return {"source": str(src), "destination": str(dst), "success": True}
    except Exception as e:
        return {"error": str(e), "success": False}


def fs_move(args: Dict) -> Dict:
    source = args.get("source")
    destination = args.get("destination")
    if not source or not destination:
        return {"error": "Missing required arguments", "success": False}
    try:
        src = Path(source).expanduser().resolve()
        dst = Path(destination).expanduser().resolve()
        if not src.exists():
            return {"error": "Source does not exist", "success": False}
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return {"source": str(src), "destination": str(dst), "success": True}
    except Exception as e:
        return {"error": str(e), "success": False}


def fs_mkdir(args: Dict) -> Dict:
    path = args.get("path")
    if not path:
        return {"error": "Missing required argument: path", "success": False}
    try:
        target = Path(path).expanduser().resolve()
        target.mkdir(parents=True, exist_ok=True)
        return {"path": str(target), "success": True}
    except Exception as e:
        return {"error": str(e), "success": False}


def fs_exists(args: Dict) -> Dict:
    path = args.get("path")
    if not path:
        return {"error": "Missing required argument: path", "success": False}
    try:
        target = Path(path).expanduser().resolve()
        return {
            "path": str(target),
            "exists": target.exists(),
            "is_file": target.is_file() if target.exists() else False,
            "is_dir": target.is_dir() if target.exists() else False,
            "success": True
        }
    except Exception as e:
        return {"error": str(e), "success": False}


def shell_execute(args: Dict) -> Dict:
    command = args.get("command")
    timeout = args.get("timeout", 30)
    workdir = args.get("workdir")
    if not command:
        return {"error": "Missing required argument: command", "success": False}
    try:
        cwd = _get_workdir(workdir)
        use_shell = "|" in command or "&&" in command or ">" in command or "<" in command
        start_time = time.time()
        result = subprocess.run(command, shell=use_shell, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        elapsed = time.time() - start_time
        return {
            "command": command,
            "exit_code": result.returncode,
            "success": result.returncode == 0,
            "elapsed_seconds": round(elapsed, 2),
            "workdir": cwd,
            "stdout": result.stdout[:50000] if len(result.stdout) > 50000 else result.stdout,
            "stderr": result.stderr[:50000] if len(result.stderr) > 50000 else result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out after {timeout}s", "success": False}
    except Exception as e:
        return {"error": str(e), "success": False}


def process_list(args: Dict) -> Dict:
    filter_name = args.get("filter_name", "").lower()
    try:
        if platform.system() == "Windows":
            result = subprocess.run(["tasklist", "/fo", "csv", "/nh"], capture_output=True, text=True)
            processes = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.strip('"').split('","')
                if len(parts) >= 2:
                    name, pid = parts[0], parts[1]
                    if filter_name and filter_name not in name.lower():
                        continue
                    processes.append({"name": name, "pid": int(pid)})
        else:
            result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
            processes = []
            for line in result.stdout.strip().split("\n")[1:]:
                if not line:
                    continue
                parts = line.split(None, 10)
                if len(parts) >= 11:
                    name = parts[10].split("/")[-1]
                    if filter_name and filter_name not in name.lower():
                        continue
                    processes.append({"user": parts[0], "pid": int(parts[1]), "name": name})
        return {"processes": processes[:100], "count": len(processes[:100]), "success": True}
    except Exception as e:
        return {"error": str(e), "success": False}


def process_kill(args: Dict) -> Dict:
    pid = args.get("pid")
    name = args.get("name")
    force = args.get("force", False)
    if not pid and not name:
        return {"error": "Missing required argument: pid or name", "success": False}
    try:
        if platform.system() == "Windows":
            cmd = ["taskkill"]
            if force:
                cmd.append("/f")
            if pid:
                cmd.extend(["/pid", str(pid)])
            elif name:
                cmd.extend(["/im", name])
            result = subprocess.run(cmd, capture_output=True, text=True)
        else:
            if pid:
                cmd = ["kill"] + (["-9"] if force else []) + [str(pid)]
            else:
                cmd = ["pkill"] + (["-9"] if force else []) + [name]
            result = subprocess.run(cmd, capture_output=True, text=True)
        return {"pid": pid, "name": name, "success": result.returncode == 0, "output": result.stdout or result.stderr}
    except Exception as e:
        return {"error": str(e), "success": False}


def system_info(args: Dict) -> Dict:
    try:
        info = {
            "system": platform.system(),
            "node": platform.node(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "python_path": sys.executable,
            "cwd": os.getcwd(),
            "home": str(Path.home()),
        }
        return {"info": info, "success": True}
    except Exception as e:
        return {"error": str(e), "success": False}


def system_disk_usage(args: Dict) -> Dict:
    path = args.get("path", "C:\\" if platform.system() == "Windows" else "/")
    try:
        usage = shutil.disk_usage(path)
        return {
            "path": path,
            "total_gb": round(usage.total / (1024**3), 2),
            "used_gb": round(usage.used / (1024**3), 2),
            "free_gb": round(usage.free / (1024**3), 2),
            "percent_used": round(usage.used / usage.total * 100, 1),
            "success": True
        }
    except Exception as e:
        return {"error": str(e), "success": False}


def register_system_tools():
    from .tool_registry import register_builtin_tool
    tools = [
        {"name": "fs_list", "description": "List directory contents", "category": "filesystem", "handler": fs_list_directory},
        {"name": "fs_read", "description": "Read file contents", "category": "filesystem", "handler": fs_read_file},
        {"name": "fs_write", "description": "Write content to a file", "category": "filesystem", "handler": fs_write_file},
        {"name": "fs_delete", "description": "Delete a file or directory", "category": "filesystem", "handler": fs_delete},
        {"name": "fs_copy", "description": "Copy a file or directory", "category": "filesystem", "handler": fs_copy},
        {"name": "fs_move", "description": "Move or rename a file or directory", "category": "filesystem", "handler": fs_move},
        {"name": "fs_mkdir", "description": "Create a new directory", "category": "filesystem", "handler": fs_mkdir},
        {"name": "fs_exists", "description": "Check if a file or directory exists", "category": "filesystem", "handler": fs_exists},
        {"name": "shell_exec", "description": "Execute a shell command", "category": "shell", "handler": shell_execute},
        {"name": "process_list", "description": "List running processes", "category": "process", "handler": process_list},
        {"name": "process_kill", "description": "Terminate a running process", "category": "process", "handler": process_kill},
        {"name": "system_info", "description": "Get system information", "category": "system", "handler": system_info},
        {"name": "system_disk_usage", "description": "Get disk space usage", "category": "system", "handler": system_disk_usage},
    ]
    for tool in tools:
        register_builtin_tool(tool)
    logger.info(f"Registered {len(tools)} system tools")
