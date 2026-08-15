import json,secrets,pathlib
p=pathlib.Path(__file__).resolve().parent/'agent_config.json'
cfg={"bind":"0.0.0.0","port":8765,"token":secrets.token_urlsafe(32),"max_clock_skew_seconds":30}
p.write_text(json.dumps(cfg,indent=2),encoding='utf-8')
print('Generated agent_config.json with a new token. Copy the token into the Android Companion app.')
print(cfg['token'])
