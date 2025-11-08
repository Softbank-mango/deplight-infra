import asyncio
from asyncio import AbstractEventLoop

from .logger import ServingLogger


async def monitor_event_loop_lag(loop: AbstractEventLoop):
    """
    main thread (eventloop) blocker warning.

    e.g.
    ::
        # app.py
        async def lifespan(app: FastAPI):
            if app_settings.LETSUR_DEBUG:
                import asyncio
                from .debug import monitor_event_loop_lag
                loop = asyncio.get_running_loop()
                loop.create_task(monitor_event_loop_lag(loop))
            yield

    https://medium.com/@DorIndivo/overcoming-performance-bottlenecks-with-async-python-a-deep-dive-into-cpu-bound-code-b604a400255a
    """
    start = loop.time()
    sleep_interval = 1

    while loop.is_running():
        await asyncio.sleep(sleep_interval)
        diff = loop.time() - start
        lag = diff - sleep_interval
        # send lag as a statsd metric
        if lag > 0.5:
            tasks = asyncio.all_tasks(loop)
            for task in tasks:
                if task._coro.cr_code.co_name != "monitor_event_loop_lag":
                    ServingLogger().warning(f"event loop lag:{lag}, task: {task}")
        start = loop.time()
