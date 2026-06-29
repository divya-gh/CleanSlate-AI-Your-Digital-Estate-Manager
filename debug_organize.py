import urllib.request, json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = 'http://127.0.0.1:8000'
APP  = 'cleanslate_ai_my_pc_assistant'
USER = 'user'

req = urllib.request.Request(f'{BASE}/apps/{APP}/users/{USER}/sessions', method='POST', headers={'Content-Type':'application/json'}, data=b'{}')
sid = json.loads(urllib.request.urlopen(req).read()).get('id')
print('session:', sid)

body = json.dumps({'app_name':APP,'user_id':USER,'session_id':sid,'new_message':{'role':'user','parts':[{'text':'organize my computer'}]}}).encode()
req2 = urllib.request.Request(f'{BASE}/run_sse', method='POST', headers={'Content-Type':'application/json'}, data=body)
with urllib.request.urlopen(req2, timeout=50) as resp:
    for i, raw in enumerate(resp):
        line = raw.decode('utf-8').strip()
        if not line.startswith('data:'): continue
        payload = line[5:].strip()
        if not payload or payload == '[DONE]': continue
        try:
            ev = json.loads(payload)
            print(f'--- Event {i} ---')
            print('  keys:', list(ev.keys()))
            out = ev.get('output') or {}
            print('  output keys:', list(out.keys()) if isinstance(out,dict) else type(out).__name__)
            hr = out.get('human_readable_report','')
            print('  human_readable_report len:', len(hr))
            parts = (ev.get('content') or {}).get('parts') or []
            for j, p in enumerate(parts):
                fc = p.get('functionCall') or {}
                txt = p.get('text','')
                fc_id = fc.get('id','')
                fc_msg_len = len((fc.get('args') or {}).get('message',''))
                print(f'  parts[{j}]: has_functionCall={bool(fc)} text_len={len(txt)} fc_id={fc_id!r} fc_msg_len={fc_msg_len}')
        except Exception as e:
            print(f'  err: {e}')
        if i > 15:
            break
print('done')
