import json
import logging
import pathlib
import re
from collections import Counter

logger = logging.getLogger(__name__)


def split_drakmon_log(analysis_dir: pathlib.Path) -> None:
    drakmon_log_path = analysis_dir / "drakmon.log"
    error_path = analysis_dir / "parse_errors.log"
    error_file = None
    plugin_files = {}
    failures = Counter()

    with drakmon_log_path.open("rb") as drakmon_log:
        for line in drakmon_log:
            try:
                line_s = line.strip().decode()
                obj = json.loads(line_s)

                plugin = obj.get("Plugin", "unknown")

                if plugin not in plugin_files:
                    plugin_files[plugin] = (
                        drakmon_log_path.with_name(f"{plugin}.log")
                    ).open("w")

                plugin_file = plugin_files[plugin]
                plugin_file.write(json.dumps(obj) + "\n")
            except (UnicodeDecodeError, json.JSONDecodeError):
                # Log the failure and count statistics

                plugin_heuristic: bytes = r'"Plugin": "(\w+)"'.encode()
                match = re.match(plugin_heuristic, line)
                if match:
                    # we've matched a unicode word, this shouldn't fail
                    plugin = match.group(1).decode("utf-8", "replace")
                else:
                    plugin = "unknown"

                failures[plugin] += 1
                if not error_file:
                    error_file = error_path.open("wb")
                error_file.write(line)

    for plugin_file in plugin_files.values():
        plugin_file.close()

    if error_file:
        error_file.close()

    for plugin, count in failures.items():
        logger.warning("Failed to parse %d lines generated by %s", count, plugin)
    # Remove drakmon.log is successfully split
    drakmon_log_path.unlink()
