"""
Generate interactive PWA for GitHub Pages.
Full Commit Device: lock(progress bar), execute, override, quarantine.
Calls local API (http://192.168.1.5:8766) when on same WiFi.
"""
import json, datetime, os, requests, sys

HERE = os.path.dirname(__file__)
LOCAL_API = 'http://192.168.1.5:8766'
FALLBACK_API = 'http://127.0.0.1:8766'

def fetch():
    # Try local first, then fallback
    api = LOCAL_API
    try:
        r = requests.get(f'{LOCAL_API}/api/state', timeout=3)
    except:
        try:
            r = requests.get(f'{FALLBACK_API}/api/state', timeout=3)
            api = FALLBACK_API
        except:
            api = None

    if api:
        plan = requests.get(f'{api}/api/plan').json()
        bw = requests.get(f'{api}/api/buywatch').json()
        stats = requests.get(f'{api}/api/stats').json()
        export = requests.get(f'{api}/api/export').json()
        q = requests.get(f'{api}/api/quarantine').json()
    else:
        plan = {'date': datetime.datetime.now().strftime('%Y-%m-%d'), 'items': [], 'locked': False, 'content': ''}
        bw = {'items': [], 'max': 6}
        stats = {'streak': 0, 'month_overrides': 0}
        export = {'action_log': [], 'overrides': []}
        q = {'active': False}

    return {
        'plan': plan, 'buywatch': bw.get('items', []), 'bw_max': bw.get('max', 6),
        'stats': stats, 'log': export.get('action_log', [])[:50],
        'overrides': export.get('overrides', [])[:20],
        'quarantine': q,
        'api': api,
        'generated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    }

def build(data):
    plan = data['plan']; bw = data['buywatch']; stats = data['stats']
    plan_locked = plan.get('locked', False)
    api = data.get('api')

    # Offline fallback
    offline_note = ''
    if not api:
        offline_note = '<div style="background:rgba(255,59,48,.08);border:1px solid rgba(255,59,48,.2);color:#FF3B30;padding:8px 14px;margin:8px 16px;font-size:10px;font-family:monospace;text-align:center;border-radius:4px">⚠ 未连接到本地服务器 · 仅查看模式<br>请确保手机与电脑在同一WiFi</div>'

    # Countdown
    now_ts = datetime.datetime.now().timestamp()
    mo = datetime.datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    next_open = mo if now_ts < mo.timestamp() else (mo + datetime.timedelta(days=1))
    secs_to_open = max(0, int(next_open.timestamp() - now_ts))
    h_to, m_to = secs_to_open // 3600, (secs_to_open % 3600) // 60
    countdown_text = f'{h_to}时{m_to}分' if secs_to_open > 0 else '已开盘'
    if datetime.datetime.now().weekday() >= 5:
        mon = datetime.datetime.now() + datetime.timedelta(days=(7-datetime.datetime.now().weekday()))
        countdown_text = f'周{["一","二","三","四","五","六","日"][mon.weekday()]} {mon.strftime("%m/%d")}'

    q = data.get('quarantine', {})
    in_q = q.get('active', False)

    # Items with data-wall + interactive
    items_html = ''
    for it in plan.get('items', []):
        a = it['action']; code = it['code']; name = it['name']; reason = it.get('reason','')
        status = it.get('status','pending'); item_id = it.get('id', 0)
        is_critical = it.get('critical', False)

        if a in ('清仓','卖出'): row_cls = 'sell'; badge_cls = 'badge-sell'
        elif a == '减仓': row_cls = 'reduce'; badge_cls = 'badge-reduce'
        elif a == '买入': row_cls = 'buy'; badge_cls = 'badge-buy'
        else: row_cls = 'hold'; badge_cls = 'badge-hold'

        if status == 'done' or f'executed.indexOf({item_id})' in locals():
            row_cls += ' executed'
            action_html = f'<span class="exec-tag done-tag">✓</span>'
        elif status == 'overridden':
            row_cls += ' overridden'
            action_html = f'<span class="exec-tag override-tag">⚠</span>'
        else:
            # Always render execute button, hidden by default, shown when locked
            action_html = f'<span class="exec-btn-placeholder" style="display:none" onclick="execItem({item_id})">执行</span>'

        crit_border = ' critical' if is_critical else ''

        items_html += f'''<div class="item {row_cls}{crit_border}" data-id="{item_id}">
            <div class="item-left"><span class="badge {badge_cls}">{a}</span></div>
            <div class="item-main">
                <div class="item-head"><span class="code">{code}</span> <span class="name">{name}</span> {action_html}</div>
                <div class="item-meta">{reason}</div>
            </div>
            <span class="override-link" onclick="openOverride({item_id},'{code}','{name}')" title="覆盖">✎</span>
        </div>'''

    # BUY WATCH
    bw_html = ''
    for b in bw:
        bw_html += f'''<div class="buy-item">
            <div class="bw-top"><span class="code">{b['code']}</span> {b['name']}<span class="eta">{b.get('eta','')}</span></div>
            <div class="trigger">{b.get('trigger_cond','')}</div>
        </div>'''

    # State
    state_label = 'LOCKED 🔒' if plan_locked else 'PREP'
    state_cls = 'state-locked' if plan_locked else 'state-prep'

    q_html = ''
    if in_q:
        q_html = f'''<div class="quarantine-banner">
            <div class="q-title">⚠ QUARANTINE ACTIVE</div>
            <div class="q-detail">{q.get('trigger_tag','')} · 至 {q.get('expires_at','')}</div>
            <div class="q-info">计划外操作已冻结</div>
        </div>'''

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no,viewport-fit=cover">
<title>Lobster Commit</title>
<link rel="apple-touch-icon" href="icons/icon-192x192.png">
<link rel="manifest" href="./manifest.json">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Commit">
<meta name="theme-color" content="#080B0F">
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Noto+Sans+SC:wght@400;500;700&display=swap');
*{{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}}
body{{font-family:'Noto Sans SC',-apple-system,sans-serif;background:#05080C;color:#E8ECF2;min-height:100vh;padding-bottom:140px;overflow-x:hidden}}
.header{{display:flex;justify-content:space-between;align-items:flex-start;padding:14px 16px 10px;background:rgba(5,8,12,.94);backdrop-filter:blur(12px);position:sticky;top:0;z-index:10;border-bottom:1px solid #1C2532}}
.header .date{{font-family:'JetBrains Mono',monospace;font-size:15px;font-weight:700}}
.header .countdown{{font-family:'JetBrains Mono',monospace;font-size:10px;color:#FF9F0A}}
.state-badge{{padding:3px 10px;font-size:9px;font-family:'JetBrains Mono',monospace;font-weight:700;letter-spacing:1.5px;border-radius:2px}}
.state-prep{{background:rgba(110,118,136,.12);color:#7A8290;border:1px solid #1C2532}}
.state-locked{{background:rgba(255,159,10,.1);color:#FF9F0A;border:1px solid rgba(255,159,10,.2)}}
.quarantine-banner{{margin:8px 16px;padding:14px;background:rgba(255,59,48,.06);border:1px solid rgba(255,59,48,.2);border-radius:4px;text-align:center}}
.q-title{{font-family:'JetBrains Mono',monospace;font-size:14px;font-weight:700;color:#FF3B30;letter-spacing:2px;margin-bottom:4px}}
.q-detail{{font-size:11px;color:rgba(255,59,48,.6);margin-bottom:6px;font-family:'JetBrains Mono',monospace}}
.q-info{{font-size:10px;color:rgba(255,59,48,.3)}}
.lock-banner{{display:flex;align-items:center;justify-content:center;gap:8px;padding:8px 16px;margin:8px 16px;background:rgba(255,159,10,.06);border:1px solid rgba(255,159,10,.15);border-radius:4px;font-size:11px;font-family:'JetBrains Mono',monospace;color:#FF9F0A;letter-spacing:1px}}
.tab-bar{{display:flex;margin:8px 16px;background:#0D1117;border-radius:6px;padding:3px;border:1px solid #1C2532}}
.tab-radio{{display:none}}
.tab-radio:checked+.tab-label{{background:#141B24;color:#E8ECF2}}
.tab-label{{flex:1;text-align:center;padding:8px;font-size:11px;font-weight:600;color:#7A8290;cursor:pointer;border-radius:4px;transition:.15s;font-family:'JetBrains Mono',monospace;letter-spacing:.5px;display:block}}
.tab-panel{{display:none;padding:0 16px}}
#tr0:checked~#tp0{{display:block}}
#tr1:checked~#tp1{{display:block}}
#tr2:checked~#tp2{{display:block}}

.item{{display:flex;gap:10px;align-items:flex-start;padding:10px 8px;border-bottom:1px solid rgba(28,37,50,.35);font-size:12px;transition:all .15s;border-radius:2px;margin-bottom:1px}}
.item.sell{{background:rgba(255,59,48,.04)}}
.item.reduce{{background:rgba(255,159,10,.03)}}
.item.hold{{background:rgba(48,209,88,.02)}}
.item.buy{{background:rgba(10,132,255,.04)}}
.item.executed{{opacity:.45}}
.item.executed .item-head{{text-decoration:line-through}}
.item.overridden{{opacity:.55;background:rgba(255,59,48,.02)}}
.item.critical{{border-left:3px solid #FF3B30;padding-left:6px}}
.item-left{{flex-shrink:0;min-width:40px}}
.badge{{display:inline-block;font-size:9px;font-weight:700;padding:2px 8px;border-radius:2px;font-family:'JetBrains Mono',monospace;letter-spacing:.5px}}
.badge-sell{{background:rgba(255,59,48,.15);color:#FF3B30}}
.badge-reduce{{background:rgba(255,159,10,.12);color:#FF9F0A}}
.badge-hold{{background:rgba(48,209,88,.1);color:#30D158}}
.badge-buy{{background:rgba(10,132,255,.12);color:#0A84FF}}
.item-main{{flex:1;min-width:0}}
.item-head{{font-size:12px;font-weight:500;margin-bottom:2px}}
.item-head .code{{font-family:'JetBrains Mono',monospace;font-size:11px;color:#0A84FF}}
.item-head .name{{font-size:12px}}
.item-meta{{font-size:10px;color:#7A8290;line-height:1.4}}
.exec-tag{{font-size:8px;font-family:'JetBrains Mono',monospace;margin-left:6px}}
.done-tag{{color:#30D158}}
.override-tag{{color:#FF3B30}}
.exec-btn-placeholder{{font-size:9px;font-weight:700;padding:3px 8px;border:1px solid #30D158;border-radius:3px;color:#30D158;cursor:pointer;font-family:'JetBrains Mono',monospace;background:rgba(48,209,88,.08);transition:all .15s;display:none}}
.exec-btn-placeholder:active{{background:rgba(48,209,88,.2)}}
.conn-dot{{display:inline-block;width:6px;height:6px;border-radius:50%;margin-right:4px;vertical-align:middle}}
.conn-on{{background:#30D158}}.conn-off{{background:#FF3B30}}
.override-link{{font-size:9px;color:#485268;cursor:pointer;padding:2px 6px;border:1px solid transparent;font-family:'JetBrains Mono',monospace;flex-shrink:0;border-radius:2px}}
.override-link:hover{{color:#FF3B30;border-color:rgba(255,59,48,.3)}}

.buy-item{{padding:10px 8px;border-bottom:1px solid rgba(28,37,50,.3);background:#0D1117;border-radius:4px;margin-bottom:4px}}
.buy-item .bw-top{{display:flex;justify-content:space-between;align-items:center;font-size:12px;margin-bottom:4px}}
.buy-item .code{{font-family:'JetBrains Mono',monospace;font-weight:700;color:#E8ECF2}}
.buy-item .eta{{font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;color:#FF9F0A}}
.buy-item .trigger{{font-size:10px;color:#7A8290;line-height:1.5}}

.stats-row{{display:flex;gap:8px;margin-bottom:12px}}
.stat-card{{flex:1;text-align:center;padding:14px 8px;background:#0D1117;border:1px solid #1C2532;border-radius:4px}}
.stat-card .v{{font-family:'JetBrains Mono',monospace;font-size:26px;font-weight:700}}
.stat-card .l{{font-size:9px;color:#7A8290;text-transform:uppercase;letter-spacing:.5px;margin-top:2px;font-family:'JetBrains Mono',monospace}}
.section-title{{font-size:10px;font-weight:700;color:#7A8290;text-transform:uppercase;letter-spacing:1px;font-family:'JetBrains Mono',monospace;margin-bottom:8px}}
.log-line{{font-size:9px;color:#7A8290;padding:2px 0;font-family:'JetBrains Mono',monospace;border-bottom:1px solid rgba(28,37,50,.2)}}
.log-time{{color:#485268;margin-right:4px}}

.float-lock{{position:fixed;bottom:20px;left:16px;right:16px;z-index:100}}
.lock-btn{{position:relative;display:block;width:100%;padding:16px;font-size:15px;font-weight:700;cursor:pointer;border:2px solid #FF9F0A;background:rgba(5,8,12,.96);color:#FF9F0A;letter-spacing:2px;font-family:'JetBrains Mono',monospace;text-transform:uppercase;border-radius:6px;text-align:center;backdrop-filter:blur(12px);box-shadow:0 0 40px rgba(255,159,10,.08);overflow:hidden}}
.lock-btn:active{{transform:scale(.96)}}
.lock-btn .progress{{position:absolute;bottom:0;left:0;height:4px;background:rgba(255,159,10,.8);width:0%}}
.lock-btn .sub{{font-size:9px;opacity:.5;display:block;margin-top:4px;letter-spacing:1px;font-weight:400;position:relative;z-index:1}}
.lock-btn.locked{{border-color:#485268;color:#485268;box-shadow:none;pointer-events:none}}
@keyframes lock-pulse{{0%,100%{{box-shadow:0 0 24px rgba(255,159,10,.06)}}50%{{box-shadow:0 0 48px rgba(255,159,10,.15)}}}}
.lock-btn:not(.locked){{animation:lock-pulse 3s ease-in-out infinite}}

.toast{{position:fixed;top:20px;left:50%;transform:translateX(-50%);background:#FF9F0A;color:#05080C;padding:10px 24px;border-radius:20px;font-weight:700;font-family:'JetBrains Mono',monospace;font-size:13px;z-index:200;opacity:0;transition:opacity .3s;pointer-events:none}}
.toast.show{{opacity:1}}
.install-banner{{display:none;align-items:center;justify-content:space-between;padding:10px 16px;margin:0 16px 8px;background:#0D1117;border:1px solid #FF9F0A;border-radius:6px;font-size:12px;color:#FF9F0A;font-family:'JetBrains Mono',monospace}}

/* Override modal */
.modal-overlay{{position:fixed;inset:0;background:rgba(5,8,12,.95);z-index:150;display:none;align-items:center;justify-content:center}}
.modal-overlay.active{{display:flex}}
.modal{{background:#0D1117;border:1px solid #1C2532;padding:20px;margin:16px;border-radius:6px;max-width:340px}}
.modal h3{{font-size:14px;font-weight:700;color:#FF3B30;font-family:'JetBrains Mono',monospace;margin-bottom:8px}}
.modal .tags{{display:flex;gap:6px;flex-wrap:wrap;margin:12px 0}}
.modal .tag{{padding:6px 14px;border-radius:14px;font-size:11px;cursor:pointer;border:1px solid #1C2532;background:#05080C;color:#7A8290;font-family:'JetBrains Mono',monospace;transition:.15s}}
.modal .tag.selected{{border-color:#FF3B30;background:rgba(255,59,48,.1);color:#FF3B30}}
.modal .btn-row{{display:flex;gap:8px;margin-top:12px}}
.modal .btn-confirm{{flex:1;padding:12px;border-radius:4px;font-size:12px;font-weight:700;cursor:pointer;border:none;background:#FF3B30;color:#fff;opacity:.3;pointer-events:none;font-family:'JetBrains Mono',monospace}}
.modal .btn-confirm.ready{{opacity:1;pointer-events:auto}}
.modal .btn-cancel{{flex:1;padding:12px;border-radius:4px;font-size:12px;cursor:pointer;border:1px solid #1C2532;background:transparent;color:#7A8290;font-family:'JetBrains Mono',monospace}}
</style></head>
<body onload="countdownTick();setInterval(countdownTick,60000)">
<div class="header">
    <div><div class="date">{plan["date"]} · MONDAY</div><div class="countdown" id="countdown">距离开盘 {countdown_text}</div></div>
    <div class="state-badge {state_cls}" id="stateBadge">{state_label}</div>
</div>

<div id="connStatus" style="text-align:center;padding:4px;font-size:9px;font-family:'JetBrains Mono',monospace"></div>
<div style="text-align:center;padding:4px;font-size:8px;font-family:monospace"><span id=\"verTag\" style=\"color:#485268\">v?</span> · <a href=\"javascript:navigator.serviceWorker.getRegistrations().then(r=>r.forEach(x=>x.unregister()));caches.keys().then(k=>k.forEach(x=>caches.delete(x)));location.reload();\" style=\"color:#FF3B30;text-decoration:none\">硬核重置</a></div>
{offline_note}
{q_html}
{'<div class="lock-banner">🔒 计划已封印 · 盘中只执行计划内操作</div>' if plan_locked else ''}

<input type="radio" class="tab-radio" name="tab" id="tr0" checked>
<input type="radio" class="tab-radio" name="tab" id="tr1">
<input type="radio" class="tab-radio" name="tab" id="tr2">
<div class="tab-bar">
    <label class="tab-label" for="tr0">📋 计划</label>
    <label class="tab-label" for="tr1">🎯 候选</label>
    <label class="tab-label" for="tr2">📊 状态</label>
</div>

<div class="tab-panel" id="tp0">{items_html}</div>
<div class="tab-panel" id="tp1">{bw_html if bw else '<div style="color:#7A8290;font-size:12px;text-align:center;padding:30px;font-family:monospace">等待选股</div>'}</div>
<div class="tab-panel" id="tp2">
    <div class="stats-row">
        <div class="stat-card"><div class="v" style="color:#30D158">{stats.get("streak",0)}</div><div class="l">连续遵守</div></div>
        <div class="stat-card"><div class="v" style="color:#FF3B30">{stats.get("month_overrides",0)}</div><div class="l">本月覆盖</div></div>
        <div class="stat-card"><div class="v" style="color:#0A84FF">{len(bw)}</div><div class="l">候选</div></div>
    </div>
    <div class="section-title">操作日志</div>
    {''.join(f'<div class="log-line"><span class="log-time">{l["time"][-8:]}</span> {l["action"]}: {l["detail"]}</div>' for l in data['log'][:15])}
</div>

<div class="float-lock">
    <div class="lock-btn {'locked' if plan_locked else ''}" id="lockBtn"
         ontouchstart="startHold()" ontouchend="cancelHold()" ontouchmove="cancelHold()"
         onmousedown="startHold()" onmouseup="cancelHold()" onmouseleave="cancelHold()">
        <span style="position:relative;z-index:1">{'🔒 已封印' if plan_locked else '🔓 封印计划'}</span>
        <div class="sub" style="position:relative;z-index:1">{'盘中照此执行' if plan_locked else '按住3秒封印'}</div>
        <div class="progress" id="lockProgress"></div>
    </div>
</div>

<div class="toast" id="toast"></div>

<div class="modal-overlay" id="overrideModal">
    <div class="modal">
        <h3>覆盖计划项</h3>
        <div id="overrideInfo" style="font-size:12px;color:#E8ECF2;margin-bottom:4px"></div>
        <div style="font-size:10px;color:#7A8290;margin-bottom:12px">选择原因后确认，将触发2小时隔离</div>
        <div class="tags" id="overrideTags">
            <div class="tag" onclick="selectTag(this)" data-tag="恐慌">恐慌</div>
            <div class="tag" onclick="selectTag(this)" data-tag="贪婪">贪婪</div>
            <div class="tag" onclick="selectTag(this)" data-tag="FOMO">FOMO</div>
            <div class="tag" onclick="selectTag(this)" data-tag="新信息">新信息</div>
            <div class="tag" onclick="selectTag(this)" data-tag="其他">其他</div>
        </div>
        <div class="btn-row">
            <button class="btn-confirm" id="overrideConfirm" onclick="submitOverride()">确认覆盖</button>
            <button class="btn-cancel" onclick="closeOverride()">取消</button>
        </div>
    </div>
</div>

<div class="toast" id="quarantineToast" style="position:fixed;inset:0;background:rgba(5,8,12,.98);z-index:250;display:none;flex-direction:column;align-items:center;justify-content:center;font-family:'JetBrains Mono',monospace">
    <div style="font-size:18px;color:#FF3B30;font-weight:700;letter-spacing:3px;margin-bottom:8px">QUARANTINE</div>
    <div style="font-size:48px;font-weight:700;color:#FF3B30" id="qCountdown">02:00:00</div>
    <div style="font-size:10px;color:rgba(255,59,48,.3);margin:8px 0 24px;letter-spacing:2px">计划外操作已冻结</div>
    <button onclick="closeQuarantine()" style="background:none;border:1px solid #485268;color:#7A8290;padding:8px 24px;border-radius:4px;font-size:12px;font-family:'JetBrains Mono',monospace">关闭</button>
</div>

<script>
var API = '{api or ""}';
var locked = {str(plan_locked).lower()};
var overrideItemId = null, selectedTag = '';
var qTimer = null, isOnline = false;
var localState = {{}};
try {{ localState = JSON.parse(localStorage.getItem('commit_state') || '{{"locked":false,"executed":[],"overridden":[]}}'); }} catch(e) {{}};
if (localState.locked) locked = true;

function saveState() {{ localStorage.setItem('commit_state', JSON.stringify(localState)); }}
function isExecuted(id) {{ return localState.executed.indexOf(id) !== -1; }}
function isOverridden(id) {{ return localState.overridden.indexOf(id) !== -1; }}

async function checkConn() {{
    if (!API) {{ isOnline = false; return; }}
    try {{ var r = await fetch(API + '/api/state', {{method:'GET'}}); isOnline = r.ok; }} catch(e) {{ isOnline = false; }}
    var el = document.getElementById('connStatus');
    if (el) el.innerHTML = isOnline ? '<span class="conn-dot conn-on"></span>已连接' : '<span class="conn-dot conn-off"></span>离线模式';
    if (isOnline) syncToServer();
}}
checkConn(); setInterval(checkConn, 30000);

async function apiCall(path, method, body) {{
    if (!API) return null;
    try {{
        var opts = {{method: method || 'GET', headers: {{'Content-Type': 'application/json'}}}};
        if (body) opts.body = JSON.stringify(body);
        var r = await fetch(API + path, opts);
        return r.json();
    }} catch(e) {{ return null; }}
}}

async function syncToServer() {{
    if (!isOnline) return;
    if (localState.locked) await apiCall('/api/plan/lock', 'POST', {{content:'',items:[]}});
    for (var i = 0; i < localState.executed.length; i++) await apiCall('/api/plan/execute', 'POST', {{id: localState.executed[i]}});
    for (var j = 0; j < localState.overridden.length; j++) {{
        var ov = localState.overridden[j];
        await apiCall('/api/override', 'POST', {{item_id: ov.id, code: ov.code, name: ov.name, reason: ov.tag, tag: ov.tag}});
    }}
}}

function updateUI() {{
    var items = document.querySelectorAll('.item');
    for (var i = 0; i < items.length; i++) {{
        var id = parseInt(items[i].getAttribute('data-id') || '0');
        if (isExecuted(id)) {{ items[i].classList.add('executed'); }}
        if (isOverridden(id)) {{ items[i].classList.add('overridden'); }}
    }}
    if (locked) {{
        document.getElementById('lockBtn').className = 'lock-btn locked';
        document.getElementById('lockBtn').innerHTML = '<span style=\"position:relative;z-index:1\">🔒 已封印</span><div class=\"sub\" style=\"position:relative;z-index:1\">盘中照此执行</div><div class=\"progress\"></div>';
        document.getElementById('stateBadge').textContent = 'LOCKED 🔒';
        document.getElementById('stateBadge').className = 'state-badge state-locked';
        // Show execute buttons
        var btns = document.querySelectorAll('.exec-btn-placeholder');
        for (var k = 0; k < btns.length; k++) btns[k].style.display = 'inline-block';
    }}
}}
updateUI();

// Lock with progress bar
var holdTimer = null, holdStart = 0;
function startHold() {{
    if (locked) return;
    holdStart = Date.now();
    var bar = document.getElementById('lockProgress');
    holdTimer = setInterval(function() {{
        var pct = Math.min(100, (Date.now() - holdStart) / 30);
        bar.style.width = pct + '%';
        if (pct >= 100) {{ cancelHold(); triggerLock(); }}
    }}, 50);
}}
function cancelHold() {{
    clearInterval(holdTimer); holdTimer = null;
    document.getElementById('lockProgress').style.width = '0%';
}}
function triggerLock() {{
    cancelHold();
    if (navigator.vibrate) navigator.vibrate([30,50,30,50,100]);
    showToast('🔒 计划已封印');
    locked = true;
    localState.locked = true; saveState();
    document.getElementById('lockBtn').className = 'lock-btn locked';
    document.getElementById('lockBtn').innerHTML = '<span style=\"position:relative;z-index:1\">🔒 已封印</span><div class=\"sub\" style=\"position:relative;z-index:1\">盘中照此执行</div><div class=\"progress\"></div>';
    document.getElementById('stateBadge').textContent = 'LOCKED 🔒';
    document.getElementById('stateBadge').className = 'state-badge state-locked';
    document.getElementById('lockProgress').style.width = '0%';
    var btns = document.querySelectorAll('.exec-btn-placeholder');
    for (var k = 0; k < btns.length; k++) btns[k].style.display = 'inline-block';
    apiCall('/api/plan/lock', 'POST', {{content: '', items: []}});
}}

// Execute item
function execItem(id) {{
    if (!locked) {{ showToast('请先封印计划'); return; }}
    if (isExecuted(id)) return;
    if (navigator.vibrate) navigator.vibrate(50);
    localState.executed.push(id); saveState();
    var item = document.querySelector('.item[data-id=\"' + id + '\"]');
    if (item) {{ item.classList.add('executed'); var b = item.querySelector('.exec-btn-placeholder'); if (b) b.style.display = 'none'; }}
    showToast('✓ 已执行');
    apiCall('/api/plan/execute', 'POST', {{id: id}});
}}

// Override
function openOverride(id, code, name) {{
    overrideItemId = id; selectedTag = '';
    document.getElementById('overrideInfo').textContent = code + ' ' + name;
    document.querySelectorAll('#overrideTags .tag').forEach(function(t){{ t.classList.remove('selected'); }});
    document.getElementById('overrideConfirm').classList.remove('ready');
    document.getElementById('overrideModal').classList.add('active');
}}
function closeOverride() {{ document.getElementById('overrideModal').classList.remove('active'); }}
function selectTag(el) {{
    document.querySelectorAll('#overrideTags .tag').forEach(function(t){{ t.classList.remove('selected'); }});
    el.classList.add('selected'); selectedTag = el.dataset.tag;
    document.getElementById('overrideConfirm').classList.add('ready');
}}
async function submitOverride() {{
    if (!selectedTag) return;
    var info = document.getElementById('overrideInfo').textContent.split(' ');
    var r = await apiCall('/api/override', 'POST', {{item_id: overrideItemId, code: info[0], name: info[1], reason: selectedTag, tag: selectedTag}});
    closeOverride();
    if (r && r.quarantine_triggered) {{
        document.getElementById('quarantineToast').style.display = 'flex';
        startQCountdown(r.quarantine_expires);
    }}
    if (r && r.ok) {{ showToast('已覆盖 · 隔离触发'); setTimeout(function(){{ location.reload(); }}, 1000); }}
}}

// Quarantine countdown
function startQCountdown(exp) {{
    if (qTimer) clearInterval(qTimer);
    function tick() {{
        var d = Math.max(0, (new Date(exp) - new Date()) / 1000);
        if (d <= 0) {{ document.getElementById('quarantineToast').style.display = 'none'; clearInterval(qTimer); return; }}
        var h = Math.floor(d/3600), m = Math.floor((d%3600)/60), s = Math.floor(d%60);
        document.getElementById('qCountdown').textContent = String(h).padStart(2,'0')+':'+String(m).padStart(2,'0')+':'+String(s).padStart(2,'0');
    }}
    tick(); qTimer = setInterval(tick, 1000);
}}
function closeQuarantine() {{ document.getElementById('quarantineToast').style.display = 'none'; }}

// Countdown
function countdownTick() {{
    var now = new Date();
    var mo = new Date(now); mo.setHours(9,0,0,0);
    var next = mo > now ? mo : new Date(mo.getTime() + 86400000);
    var secs = Math.max(0, Math.floor((next - now) / 1000));
    var h = Math.floor(secs / 3600), m = Math.floor((secs % 3600) / 60);
    if (now.getDay() >= 5) {{
        var d = (8 - now.getDay()) % 7 || 7;
        document.getElementById('countdown').textContent = '距离开盘 ' + d + '天';
    }} else {{
        document.getElementById('countdown').textContent = '距离开盘 ' + h + '时' + m + '分';
    }}
}}

// Utility
// Tabs use pure CSS radio buttons - no JS needed
function showToast(msg) {{
    var t = document.getElementById('toast');
    t.textContent = msg; t.classList.add('show');
    setTimeout(function(){{ t.classList.remove('show'); }}, 2000);
}}

// Install PWA
var deferredPrompt = null;
window.addEventListener('beforeinstallprompt', function(e){{
    e.preventDefault(); deferredPrompt = e;
    var b = document.createElement('div');
    b.className = 'install-banner'; b.style.display = 'flex'; b.innerHTML = '<span>📱 安装到桌面</span><button onclick="installApp()" style="background:#FF9F0A;color:#05080C;border:none;padding:6px 14px;border-radius:4px;font-weight:700;font-family:\'JetBrains Mono\',monospace;cursor:pointer">安装</button>';
    document.body.insertBefore(b, document.body.firstChild);
}});
function installApp() {{
    if (deferredPrompt){{ deferredPrompt.prompt(); deferredPrompt.userChoice.then(function(r){{ }}); }}
}}

if ('serviceWorker' in navigator) {{ navigator.serviceWorker.register('./sw.js?t=9'); }}
document.getElementById('verTag').textContent = 'v9';
// Load quarantine state
(function() {{
    if (apiCall) {{
        apiCall('/api/quarantine', 'GET').then(function(q) {{
            if (q && q.active) startQCountdown(q.expires_at);
        }});
    }}
}})();
</script>
</body></html>'''

if __name__ == '__main__':
    data = fetch()
    html = build(data)
    out = os.path.join(HERE, 'index.html')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    p = data['plan']; bw_items = data['buywatch']
    print(f'Generated: {out} ({len(html)} bytes)')
    print('Plan: ' + str(len(p.get('items',[]))) + ' items, locked=' + str(p.get('locked',False)))
    print('API: ' + str(data.get('api', 'OFFLINE')))
