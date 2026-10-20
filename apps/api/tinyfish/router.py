def choose(*,source_known:bool,publicly_readable:bool,interaction_required:bool,multi_step:bool)->dict:
    if multi_step:return {"capability":"agent","reason":"The investigation requires bounded multi-step navigation."}
    if interaction_required:return {"capability":"browser","reason":"The approved source requires public form interaction."}
    if source_known and publicly_readable:return {"capability":"fetch","reason":"An approved readable source URL is known."}
    return {"capability":"search","reason":"A suitable approved source must first be discovered."}
