"""
Generate PWA static site for GitHub Pages.
Tabbed interface: 计划区 / BUY WATCH / 状态面板
Floating lock button with haptic feedback.
"""
import json, datetime, os, sys
import requests

HERE = os.path.dirname(__file__)
API = 'http://127.0.0.1:8766'

def fetch():
    plan = requests.get(f'{API}/api/plan').json()
    bw = requests.get(f'{API}/api/buywatch').json()
    stats = requests.get(f'{API}/api/stats').json()
    export = requests.get(f'{API}/api/export').json()
    return {
        'plan': plan,
        'buywatch': bw.get('items', []),
        'bw_max': bw.get('max', 6),
        'stats': stats,
        'log': export.get('action_log', [])[:30],
        'overrides': export.get('overrides', [])[:20],
        'generated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    }

def build(data):
    plan = data['plan']; bw = data['buywatch']; stats = data['stats']
    plan_locked = plan.get('locked', False)
    pdata = plan

    # ── Tab 1: 计划项 ──
    items_html = ''
    for it in plan.get('items', []):
        a = it['action']
        if a in ('清仓','卖出'): row, pill = 'sell', 'pill-sell'
        elif a == '减仓': row, pill = 'reduce', 'pill-reduce'
        else: row, pill = 'hold', 'pill-hold'
        crit = ' critical' if it.get('critical') else ''
        items_html += f'<div class="item {row}{crit}"><div class="body"><div class="title">{a} <span class="code">{it["code"]}</span> {it["name"]}</div><div class="meta">{it.get("reason","")}</div></div><span class="pill {pill}">{a}</span></div>'

    # ── Tab 2: BUY WATCH ──
    bw_html = ''
    for b in bw:
        cond = b.get('trigger_cond', '')
        # Highlight price numbers
        import re
        cond = re.sub(r'(≈\d+[\d.]*)', r'<span class="hl">\1</span>', cond)
        cond = re.sub(r'(\d+-\d+元)', r'<span class="hl">\1</span>', cond)
        cond = re.sub(r'(\d+%)', r'<span class="hl">\1</span>', cond)
        bw_html += f'<div class="buy-item"><div class="bw-left"><span class="code">{b["code"]}</span> {b["name"]}<div class="trigger">{cond}</div></div><div class="eta">{b.get("eta","")}</div></div>'

    # ── Tab 3: 状态 ──
    log_html = ''
    for l in data['log'][:15]:
        log_html += f'<div class="log-line"><span class="log-time">{l["time"][-8:]}</span> {l["action"]}: {l["detail"]}</div>'

    ov_html = ''
    for o in data['overrides'][:10]:
        ov_html += f'<div class="log-line"><span class="log-time">{o["date"]}</span> 覆盖 {o["code"]} {o.get("name","")} · {o.get("tag","")}</div>'

    lock_badge = '🔒 已封印' if plan_locked else '🔓 封印计划'
    lock_class = 'locked' if plan_locked else ''

    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no,viewport-fit=cover">
<title>Lobster Commit</title>
<link rel="apple-touch-icon" href="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAALQAAAC0CAYAAAA9z5P2AAAACXBIWXMAAAsTAAALEwEAmpwYAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAGESURBVHgB7d0/bNNQHMDx7/3tOI6DE0BAEhJ06sBWdWBlY0FiYmFhY2NgY2NhY2NhY2FhY0FiYmFhY2NhY2HLH4EoiUMTO8T23f3OKU1Jq8R27N59P9KWyql1fet7/u557wQAAAAAAAAAAAAAAAAAAICyA2oNvUxKlNIyGwwGSa/XE6XUfuM5StVW6yB9G1DHMJkDkRCl7pVl2TkRnQqCeI9am3tNXQE5pmmKoii4+e6+HfzA7u2JfF+qukOlFgAAAAAAAAAAAEqPoLt3RSl1dya2a29r9M0m82BptwMAAAAAyi25uVlPYxkMvl5RKiWO+y/J/NfufoDaU2orN58bM5O5VogVpXI8szhTb5+UDTrv4Q6Jysq5P5DQtn1wY+Nmz4p7QuV6ZXI/e3dk9/7nq86lU3k+TpuAOlNCX56e26h7Wl3Rs0zRSe7e/Jey6w/wJcl9jqaW9riSyN3lb3fGq7O3ibwfT+cDAAAAAAAAABRKIYIez77Iredvx7Jc/jR3v8u//k7dAABQeoXM0EOknTqcPie0KuO4Z4E/6lMmAEBZHTtB5ypTPzA+StH0f6vqH+PnXQIAUFZKTKZsG6di+s7ezQcAAAAAAAAAAFBQbHN8pNzPx7bR8oJaW3CbOUMsvrbW/6yBMLFti1Ur3pGzII0n7T2E9twHAADEpxDZed4oipqcYF3b4kss1k3U2oLjVQAAUCUYfQEAqBLBMCQAAECVYORl7zKH09Dl07M3AAAAAAAAAABQNBzKcp6G9Qq8Y+3nAAAAAAAAAAAAAAAArBYdAACgCuhygBKA2eZ4EHFG+/TlGjsOswm6Lf/feXu60F/3LU6ctTImX6X17x/5A9TVbWlfjPL0Ox/Mb33p2icLeS/OOrRuGgn9b1nH4pl4XU9VAAAAfPJx3/hm+ToAAAAASUVORK5CYII=">
<link rel="manifest" href="/manifest.json">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Commit">
<meta name="theme-color" content="#05080C">
<style>
*{{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}}
body{{font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;background:#05080C;color:#E8ECF2;min-height:100vh;padding-bottom:120px;overflow-x:hidden}}
.header{{display:flex;justify-content:space-between;align-items:center;padding:12px 16px 8px;position:sticky;top:0;background:rgba(5,8,12,.92);backdrop-filter:blur(12px);z-index:10;border-bottom:1px solid #1C2532}}
.header .date{{font-size:15px;font-weight:700;font-family:monospace}}
.header .gen{{font-size:9px;color:#485268;font-family:monospace}}
.lock-banner{{display:flex;align-items:center;justify-content:center;gap:8px;padding:10px 16px;margin:8px 16px;background:rgba(255,159,10,.06);border:1px solid rgba(255,159,10,.15);border-radius:6px;font-size:12px;font-family:monospace;color:#FF9F0A;letter-spacing:1px}}

/* ── Tabs ── */
.tab-bar{{display:flex;margin:8px 16px;background:#0D1117;border-radius:8px;padding:3px;border:1px solid #1C2532}}
.tab-btn{{flex:1;text-align:center;padding:8px;font-size:11px;font-weight:600;color:#7A8290;cursor:pointer;border-radius:6px;transition:.2s;font-family:monospace;letter-spacing:.5px}}
.tab-btn.active{{background:#141B24;color:#E8ECF2}}
.tab-content{{display:none;padding:0 16px}}
.tab-content.active{{display:block}}

/* ── Plan card ── */
.plan-text{{font-size:13px;line-height:1.6;white-space:pre-wrap;font-family:monospace;padding:12px 16px;background:#0D1117;border:1px solid #1C2532;border-radius:6px;margin:8px 16px}}
.item{{display:flex;align-items:center;gap:8px;padding:10px 8px;border-bottom:1px solid rgba(28,37,50,.4);font-size:12px}}
.item:last-child{{border-bottom:none}}
.item.sell{{background:rgba(255,59,48,.04);border-radius:4px;margin-bottom:2px}}
.item.reduce{{background:rgba(255,159,10,.03);border-radius:4px;margin-bottom:2px}}
.item.hold{{background:rgba(48,209,88,.02);border-radius:4px;margin-bottom:2px}}
.item .body{{flex:1;min-width:0}}
.item .body .title{{font-size:12px;font-weight:500}}
.item .body .title .code{{font-family:monospace;font-size:10px;color:#0A84FF;margin:0 3px}}
.item .body .meta{{font-size:10px;color:#7A8290;line-height:1.4;margin-top:1px}}
.item.critical{{border-left:3px solid #FF3B30;padding-left:6px}}
.pill{{font-size:8px;font-weight:700;padding:2px 6px;border-radius:8px;font-family:monospace;flex-shrink:0}}
.pill-sell{{background:rgba(255,59,48,.15);color:#FF3B30}}
.pill-reduce{{background:rgba(255,159,10,.12);color:#FF9F0A}}
.pill-hold{{background:rgba(48,209,88,.1);color:#30D158}}

/* ── BUY WATCH ── */
.buy-item{{display:flex;justify-content:space-between;align-items:flex-start;padding:10px 8px;border-bottom:1px solid rgba(28,37,50,.3);font-size:11px;background:#0D1117;border-radius:4px;margin-bottom:4px}}
.buy-item:last-child{{border-bottom:none;margin-bottom:0}}
.buy-item .bw-left{{flex:1;min-width:0}}
.buy-item .code{{font-family:monospace;font-weight:700;color:#E8ECF2;font-size:12px}}
.buy-item .trigger{{color:#7A8290;font-size:10px;margin-top:3px;line-height:1.5}}
.buy-item .trigger .hl{{color:#FF9F0A;font-weight:600;font-family:monospace}}
.buy-item .eta{{font-family:monospace;font-size:11px;font-weight:700;color:#FF9F0A;margin-left:8px;text-align:right;min-width:65px}}

/* ── Status ── */
.stats-row{{display:flex;gap:8px;margin-bottom:12px}}
.stat-card{{flex:1;text-align:center;padding:14px 8px;background:#0D1117;border:1px solid #1C2532;border-radius:6px}}
.stat-card .v{{font-family:monospace;font-size:28px;font-weight:700}}
.stat-card .l{{font-size:9px;color:#7A8290;text-transform:uppercase;letter-spacing:.5px;margin-top:3px;font-family:monospace}}
.section-title{{font-size:10px;font-weight:700;color:#7A8290;text-transform:uppercase;letter-spacing:1px;font-family:monospace;margin-bottom:8px}}
.log-line{{font-size:10px;color:#7A8290;padding:3px 0;font-family:monospace;border-bottom:1px solid rgba(28,37,50,.2)}}
.log-time{{color:#485268;margin-right:6px}}

/* ── Floating Lock ── */
.float-lock{{position:fixed;bottom:20px;left:16px;right:16px;z-index:100}}
.lock-btn{{display:block;width:100%;padding:16px;font-size:16px;font-weight:700;cursor:pointer;border:2px solid #FF9F0A;background:rgba(5,8,12,.96);color:#FF9F0A;letter-spacing:2px;font-family:monospace;text-transform:uppercase;border-radius:8px;text-align:center;backdrop-filter:blur(12px);box-shadow:0 0 40px rgba(255,159,10,.1);transition:all .3s}}
.lock-btn:active{{transform:scale(.96);background:rgba(255,159,10,.1)}}
.lock-btn.locked{{border-color:#485268;color:#485268;box-shadow:none;cursor:default;pointer-events:none}}
.lock-btn .sub{{font-size:9px;opacity:.4;display:block;margin-top:4px;letter-spacing:1px;font-weight:400}}
@keyframes pulse{{0%,100%{{box-shadow:0 0 24px rgba(255,159,10,.06)}}50%{{box-shadow:0 0 48px rgba(255,159,10,.15)}}}}
.lock-btn:not(.locked){{animation:pulse 3s ease-in-out infinite}}

/* ── Toast ── */
.toast{{position:fixed;top:20px;left:50%;transform:translateX(-50%);background:#FF9F0A;color:#05080C;padding:10px 24px;border-radius:20px;font-weight:700;font-family:monospace;font-size:13px;z-index:200;opacity:0;transition:opacity .3s;pointer-events:none}}
.toast.show{{opacity:1}}
.install-banner{{display:flex;align-items:center;justify-content:space-between;padding:10px 16px;margin:0 16px 8px;background:#0D1117;border:1px solid #FF9F0A;border-radius:8px;font-size:13px;color:#FF9F0A;font-family:monospace}}
</style></head>
<body>
<div class="header"><div class="date">{plan["date"]} · MONDAY</div><div class="gen">{data["generated_at"]}</div></div>
{'<div class="lock-banner">🔒 计划已封印 · 盘中只执行计划内操作</div>' if plan_locked else ''}

<div class="tab-bar">
  <div class="tab-btn active" onclick="switchTab(0,this)">📋 计划区</div>
  <div class="tab-btn" onclick="switchTab(1,this)">🎯 BUY WATCH</div>
  <div class="tab-btn" onclick="switchTab(2,this)">📊 状态</div>
</div>

<div class="tab-content active" id="tab0">
  <div class="plan-text">{plan.get('content','').replace('&','&amp;').replace('<','&lt;')}</div>
  <div style="margin:8px 0">{items_html}</div>
</div>

<div class="tab-content" id="tab1">
  <div style="margin:8px 0">{bw_html if bw else '<div style="color:#7A8290;font-size:12px;text-align:center;padding:20px;font-family:monospace">-- 等待周末选股 --</div>'}</div>
</div>

<div class="tab-content" id="tab2">
  <div class="stats-row">
    <div class="stat-card"><div class="v" style="color:#30D158">{stats.get("streak",0)}</div><div class="l">连续遵守</div></div>
    <div class="stat-card"><div class="v" style="color:#FF3B30">{stats.get("month_overrides",0)}</div><div class="l">本月覆盖</div></div>
    <div class="stat-card"><div class="v" style="color:#0A84FF">{len(bw)}</div><div class="l">Watch</div></div>
  </div>
  <div class="section-title">操作日志</div>
  {log_html if log_html else '<div class="log-line" style="color:#485268">暂无</div>'}
  <div class="section-title" style="margin-top:16px">覆盖历史</div>
  {ov_html if ov_html else '<div class="log-line" style="color:#485268">暂无</div>'}
</div>

<div class="float-lock">
  <div class="lock-btn {lock_class}" id="lockBtn" onclick="handleLock()">
    {lock_badge}
    <div class="sub">{'计划已封印 · 盘中照此执行' if plan_locked else '长按3秒封印计划'}</div>
  </div>
</div>

<div class="toast" id="toast"></div>

<div class="install-banner" id="installBanner" style="display:none">
  <span>📱 安装到桌面</span>
  <button onclick="installApp()" style="background:#FF9F0A;color:#05080C;border:none;padding:8px 16px;border-radius:4px;font-weight:700;font-family:monospace;cursor:pointer">安装</button>
</div>

<script>
if('serviceWorker' in navigator){{navigator.serviceWorker.register('/sw.js')}}
var locked = {str(plan_locked).lower()};
var deferredPrompt = null;
window.addEventListener('beforeinstallprompt', function(e){{
  e.preventDefault();
  deferredPrompt = e;
  document.getElementById('installBanner').style.display = 'flex';
}});
function installApp(){{
  if(deferredPrompt){{
    deferredPrompt.prompt();
    deferredPrompt.userChoice.then(function(r){{
      document.getElementById('installBanner').style.display = 'none';
    }});
  }}
}}

function switchTab(n, el) {{
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  el.classList.add('active');
  document.getElementById('tab' + n).classList.add('active');
}}

var holdTimer = null;
var lockBtn = document.getElementById('lockBtn');

lockBtn.addEventListener('touchstart', function(e) {{
  if (locked) return;
  holdTimer = setTimeout(function() {{
    if (navigator.vibrate) navigator.vibrate(50);
    showToast('🔒 计划已封印');
    lockBtn.classList.add('locked');
    lockBtn.innerHTML = '🔒 已封印<div class="sub">计划已封印 · 盘中照此执行</div>';
    locked = true;
  }}, 3000);
}});

lockBtn.addEventListener('touchend', function() {{ clearTimeout(holdTimer); }});
lockBtn.addEventListener('touchmove', function() {{ clearTimeout(holdTimer); }});

function handleLock() {{
  if (!locked) {{
    if (navigator.vibrate) navigator.vibrate(30);
    showToast('请长按3秒封印');
  }}
}}

function showToast(msg) {{
  var t = document.getElementById('toast');
  t.textContent = msg; t.classList.add('show');
  setTimeout(function(){{ t.classList.remove('show'); }}, 2000);
}}
</script>
</body></html>'''

if __name__ == '__main__':
    data = fetch()
    html = build(data)
    out = os.path.join(HERE, 'index.html')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(html)
    p = data['plan']; bw_items = data['buywatch']
    print('Generated: ' + out + ' (' + str(len(html)) + ' bytes)')
    print('Plan: ' + str(len(p.get('items',[]))) + ' items, locked=' + str(p.get('locked',False)))
    print('Buy Watch: ' + str(len(bw_items)) + '/' + str(data['bw_max']))
