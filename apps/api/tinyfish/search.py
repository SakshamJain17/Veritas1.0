async def run(adapter, query, purpose="Verify an approved public source"):
    return await adapter.search(query,purpose)
