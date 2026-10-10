#!/usr/bin/env python3
"""PikaStream Key v1.0 — control OBS Desktop Audio with Scroll Lock."""

from __future__ import annotations

import configparser
import ctypes
import logging
import sys
import time
from pathlib import Path
from typing import Optional

try:
    import obsws_python as obs
except ImportError:
    print("必要なパッケージがありません。次を実行してください:")
    print("  python -m pip install obsws-python")
    raise SystemExit(1)


APP_NAME = "PikaStream Key"
APP_VERSION = "1.0"
CONFIG_PATH = Path(__file__).with_name("config.ini")
EXAMPLE_CONFIG_PATH = Path(__file__).with_name("config.ini.example")
LOG_PATH = Path(__file__).with_name("pistream_key.log")

VK_SCROLL = 0x91
HEARTBEAT_SECONDS = 5.0
RECONNECT_SECONDS = 2.0


def read_scroll_lock() -> bool:
    """Return True when Windows Scroll Lock is ON."""
    return bool(ctypes.windll.user32.GetKeyState(VK_SCROLL) & 1)


def create_config_template() -> None:
    if not CONFIG_PATH.exists():
        if EXAMPLE_CONFIG_PATH.exists():
            CONFIG_PATH.write_text(
                EXAMPLE_CONFIG_PATH.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
        else:
            parser = configparser.ConfigParser()
            parser["obs"] = {
                "host": "127.0.0.1",
                "port": "4455",
                "password": "",
                "input_name": "デスクトップ音声",
                "poll_interval": "0.25",
            }
            with CONFIG_PATH.open("w", encoding="utf-8") as file:
                parser.write(file)


def load_config() -> dict:
    parser = configparser.ConfigParser()
    if not parser.read(CONFIG_PATH, encoding="utf-8"):
        raise RuntimeError(f"設定ファイルを読み込めません: {CONFIG_PATH}")

    section = parser["obs"] if parser.has_section("obs") else {}
    host = str(section.get("host", "127.0.0.1")).strip()
    port = int(section.get("port", "4455"))
    password = str(section.get("password", ""))
    input_name = str(section.get("input_name", "デスクトップ音声")).strip()
    poll_interval = float(section.get("poll_interval", "0.25"))

    if not host:
        raise ValueError("config.ini の host が空です。")
    if not 1 <= port <= 65535:
        raise ValueError("config.ini の port は 1〜65535 にしてください。")
    if not input_name:
        raise ValueError("config.ini の input_name が空です。")
    if not 0.05 <= poll_interval <= 10:
        raise ValueError("poll_interval は 0.05〜10 秒にしてください。")

    return {
        "host": host,
        "port": port,
        "password": password,
        "input_name": input_name,
        "poll_interval": poll_interval,
    }


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_PATH, encoding="utf-8"),
        ],
    )


def desired_mute_state(scroll_lock_on: bool) -> bool:
    """Scroll Lock ON => muted; OFF => unmuted."""
    return scroll_lock_on


def connect_obs(settings: dict):
    return obs.ReqClient(
        host=settings["host"],
        port=settings["port"],
        password=settings["password"],
        timeout=3,
    )


def apply_state(client, settings: dict, scroll_lock_on: bool) -> None:
    muted = desired_mute_state(scroll_lock_on)
    client.set_input_mute(settings["input_name"], muted)
    if muted:
        logging.info("Scroll Lock: ON  | OBS「%s」: ミュート", settings["input_name"])
    else:
        logging.info("Scroll Lock: OFF | OBS「%s」: ミュート解除", settings["input_name"])


def main() -> int:
    if sys.platform != "win32":
        print("PikaStream Key は Windows 専用です。")
        return 1

    first_run = not CONFIG_PATH.exists()
    create_config_template()
    if first_run:
        print(f"設定ファイルを作成しました: {CONFIG_PATH}")
        print("config.ini を OBS の設定に合わせて編集してから、もう一度起動してください。")
        return 0

    try:
        settings = load_config()
    except (OSError, ValueError, RuntimeError, configparser.Error) as exc:
        print(f"設定エラー: {exc}")
        return 1

    setup_logging()
    logging.info("%s v%s を起動します。", APP_NAME, APP_VERSION)
    logging.info("OBS: %s:%s / 対象入力: %s",
                 settings["host"], settings["port"], settings["input_name"])
    logging.info("Scroll Lock ON = ミュート / OFF = ミュート解除")
    logging.info("終了するには Ctrl+C を押してください。")

    client: Optional[object] = None
    last_scroll_lock: Optional[bool] = None
    next_connect_at = 0.0
    next_heartbeat_at = 0.0

    try:
        while True:
            now = time.monotonic()
            scroll_lock_on = read_scroll_lock()

            if client is None and now >= next_connect_at:
                try:
                    client = connect_obs(settings)
                    logging.info("OBS WebSocket に接続しました。")
                    # On startup/reconnect, the current key state is authoritative.
                    apply_state(client, settings, scroll_lock_on)
                    last_scroll_lock = scroll_lock_on
                    next_heartbeat_at = now + HEARTBEAT_SECONDS
                except Exception as exc:
                    logging.warning("OBS に接続/同期できません: %s", exc)
                    client = None
                    next_connect_at = now + RECONNECT_SECONDS

            elif client is not None:
                try:
                    if scroll_lock_on != last_scroll_lock:
                        apply_state(client, settings, scroll_lock_on)
                        last_scroll_lock = scroll_lock_on

                    if now >= next_heartbeat_at:
                        client.get_version()
                        next_heartbeat_at = now + HEARTBEAT_SECONDS
                except Exception as exc:
                    logging.warning("OBS 接続が失われました。再接続します: %s", exc)
                    client = None
                    next_connect_at = now + RECONNECT_SECONDS

            time.sleep(settings["poll_interval"])

    except KeyboardInterrupt:
        logging.info("終了します。")
    finally:
        if client is not None:
            try:
                client.disconnect()
            except Exception:
                pass
        logging.info("%s を終了しました。", APP_NAME)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
