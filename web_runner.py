import asyncio
import os
import signal
import sys
from aiohttp import web

BOT_DIR = os.path.join(os.path.dirname(__file__), "Lyon-Discord-Manager", "bot")


async def health(request):
    proc = request.app.get("bot_process")
    return web.json_response({
        "status": "ok",
        "service": "lyon-discord-manager",
        "bot_process": "running" if proc and proc.returncode is None else "restarting",
    })


async def bot_supervisor(app):
    """Keep the web service alive and restart the bot after transient failures.

    Discord rate-limit responses (429) must not cause the Render web process to
    exit. The delay grows between attempts to avoid making a global rate limit
    worse, then resets after a stable bot session.
    """
    delay = 30
    while not app["stopping"]:
        print("[Runner] Iniciando processo do bot...", flush=True)
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-u",
            "main.py",
            cwd=BOT_DIR,
            env=os.environ.copy(),
        )
        app["bot_process"] = proc
        return_code = await proc.wait()
        app["bot_process"] = None

        if app["stopping"]:
            break

        print(
            f"[Runner] Bot terminou com código {return_code}; "
            f"nova tentativa em {delay}s.",
            flush=True,
        )
        await asyncio.sleep(delay)
        delay = min(delay * 2, 900)


async def start_bot(app):
    app["stopping"] = False
    app["bot_task"] = asyncio.create_task(bot_supervisor(app))


async def cleanup(app):
    app["stopping"] = True
    task = app.get("bot_task")
    if task:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    proc = app.get("bot_process")
    if proc and proc.returncode is None:
        proc.terminate()
        try:
            await asyncio.wait_for(proc.wait(), timeout=15)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()


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
