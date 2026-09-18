import asyncio
import os
import signal
import sys
from aiohttp import web

BOT_DIR = os.path.join(os.path.dirname(__file__), "Lyon-Discord-Manager", "bot")

async def health(request):
    return web.json_response({"status": "ok", "service": "lyon-discord-manager"})

async def start_bot(app):
    app["bot_process"] = await asyncio.create_subprocess_exec(
        sys.executable, "-u", "main.py", cwd=BOT_DIR
    )

async def cleanup(app):
    proc = app.get("bot_process")
    if proc and proc.returncode is None:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=15)
        except asyncio.TimeoutError:
            proc.kill()

async def create_app():
    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)
    app.on_startup.append(start_bot)
    app.on_cleanup.append(cleanup)
    return app

if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    web.run_app(create_app(), host="0.0.0.0", port=port)
