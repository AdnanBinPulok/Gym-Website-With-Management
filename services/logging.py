import json
import datetime
import os
import pytz
import asyncio
from colorama import Fore, Style
import traceback
import aiohttp
from aiohttp import ClientWebSocketResponse, ClientSession



localtZ = pytz.timezone('Asia/Dhaka')

class Logger:
    def __init__(self) -> None:
        if not os.path.exists("logs"):
            os.makedirs("logs")

        self.delete_old_logs(limit=10)
        self.logging_file = f"logs/{datetime.datetime.now(localtZ).strftime('%Y-%m-%d %H-%M-%S')}.log"
        self.file = open(self.logging_file, "w", encoding="utf-8")


    def delete_old_logs(self, limit=10):
        try:
            log_dir = "logs"
            if not os.path.exists(log_dir):
                return # No logs directory to clean

            log_files = sorted(
                [f for f in os.listdir(log_dir) if f.endswith(".log")],
                key=lambda x: os.path.getctime(os.path.join(log_dir, x)),
                reverse=False
            )
            for file in log_files[:-limit]:
                os.remove(os.path.join(log_dir, file))
                print(f"Deleted old log file: {file}")
        except Exception:
            print(f"Error in delete_old_logs: {traceback.format_exc()}")

    async def log(self, message, level="INFO"):
        timestamp = datetime.datetime.now(localtZ).strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] [{level}] {message}\n"

        color = {
            "INFO": Fore.LIGHTCYAN_EX,
            "WARNING": Fore.YELLOW,
            "ERROR": Fore.RED,
            "CRITICAL": Fore.MAGENTA,
            "DANGER": Fore.RED,
            "SUCCESS": Fore.GREEN,
            "DEBUG": Fore.GREEN
        }.get(level, Fore.WHITE)

        print(f"{color}{log_entry.strip()}{Style.RESET_ALL}") # .strip() to avoid double newline in print
        self.file.write(log_entry)
        self.file.flush() # Ensure log is written to disk immediately

        # Automatically start remote log server if not started and a log is attempted
        # This makes the Logger more robust if start() isn't explicitly called.
        async with self._start_lock:
            if not self._is_started:
                await self.remote_log_server.start()
                self._is_started = True

        if level != "DEBUG": # Typically, DEBUG logs are not sent to remote servers
            await self.remote_log_server.send_log(message, level)

    # Simplified methods to avoid creating a new task for each log call
    # The `log` method now handles the asynchronous call to remote_log_server.send_log
    def info(self, message):
        asyncio.create_task(self.log(message, "INFO"))

    def warning(self, message):
        asyncio.create_task(self.log(message, "WARNING"))

    def error(self, message):
        asyncio.create_task(self.log(message, "ERROR"))

    def critical(self, message):
        asyncio.create_task(self.log(message, "CRITICAL"))

    def danger(self, message):
        asyncio.create_task(self.log(message, "DANGER"))

    def debug(self, message):
        asyncio.create_task(self.log(message, "DEBUG"))

    def success(self, message):
        asyncio.create_task(self.log(message, "SUCCESS"))

    async def close(self):
        self.file.write(f"Log file closed at {datetime.datetime.now(localtZ)}\n")
        self.file.close()
        # Close remote log server connection gracefully
        if self._is_started:
            await self.remote_log_server.close()
        print("Logger gracefully closed.")

# Instantiate the logger (note: you still need to await logger.start() or wait for a log call to kick it off)
logger = Logger()