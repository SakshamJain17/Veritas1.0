async def create(adapter): return await adapter.create_browser()
async def close(adapter, session_id): return await adapter.close_browser(session_id)
