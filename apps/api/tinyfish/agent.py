async def run(adapter,url,goal,schema=None): return await adapter.run_agent(url,goal,schema)
async def status(adapter,run_id): return await adapter.get_agent_run(run_id)
