"""
Generate interactive PWA for GitHub Pages.
Full Commit Device: lock(progress bar), execute, override, quarantine.
Auto-discovers local API (same WiFi or phone hotspot).
"""
import json, datetime, os, urllib.request, sys, socket

HERE = os.path.dirname(__file__)
PORT = 8766

def _http_get(url, timeout=2):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode('utf-8'))
    except Exception:
        return None

def get_local_ip():
    """获取本机当前活跃的局域网 IP（无需外网真实连通）"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        # 8.8.8.8 不需要可达，仅让内核选择出口网卡
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if not ip.startswith("127."):
            return ip
    except Exception:
        pass
    try:
        ip = socket.gethostbyname(socket.gethostname())
        if not ip.startswith("127."):
            return ip
    except Exception:
        pass
    return None

def discover_api(port=PORT):
    """Auto-discover API: LAN IP first, then hotspot IPs, then loopback."""
    candidates = []
    local_ip = get_local_ip()
    if local_ip:
        candidates.append(f"http://{local_ip}:{port}")
        # If on home WiFi (192.168.1.x), also try hotspot subnet
        if local_ip.startswith("192.168.1."):
            candidates.append(f"http://192.168.43.100:{port}")
        # If on hotspot, also try home WiFi
        if local_ip.startswith("192.168.43."):
            candidates.append(f"http://192.168.1.5:{port}")

    # Common hotspot IPs
    for ip in ["192.168.43.100", "192.168.43.101", "172.20.10.2", "172.20.10.3"]:
        url = f"http://{ip}:{port}"
        if url not in candidates:
            candidates.append(url)

    candidates.append(f"http://127.0.0.1:{port}")

    for url in candidates:
        try:
            r = _http_get(f"{url}/api/state", timeout=2)
            if r is not None:
                return url
        except Exception:
            continue
    return None

def fetch():
    api = discover_api(PORT)
    if api:
        plan = _http_get(f'{api}/api/plan')
        bw = _http_get(f'{api}/api/buywatch')
        stats = _http_get(f'{api}/api/stats')
        export = _http_get(f'{api}/api/export')
        q = _http_get(f'{api}/api/quarantine')
    else:
        plan = {'date': datetime.datetime.now().strftime('%Y-%m-%d'), 'items': [], 'locked': False, 'content': ''}
        bw = {'items': [], 'max': 6}
        stats = {'streak': 0, 'month_overrides': 0}
        export = {'action_log': [], 'overrides': []}
        q = {'active': False}

    # Generate API candidates for JS discovery
    api_candidates = []
    local_ip = get_local_ip()
    if local_ip:
        api_candidates.append(f"http://{local_ip}:{PORT}")
    api_candidates.append("http://192.168.43.100:" + str(PORT))
    api_candidates.append("http://192.168.43.101:" + str(PORT))
    api_candidates.append("http://172.20.10.2:" + str(PORT))
    api_candidates.append("http://172.20.10.3:" + str(PORT))
    api_candidates.append("http://127.0.0.1:" + str(PORT))
    # Deduplicate
    seen = set()
    api_candidates = [x for x in api_candidates if not (x in seen or seen.add(x))]

    return {
        'plan': plan, 'buywatch': bw.get('items', []), 'bw_max': bw.get('max', 6),
        'stats': stats, 'log': export.get('action_log', [])[:50],
        'overrides': export.get('overrides', [])[:20],
        'quarantine': q,
        'dual_track': plan.get('dual_track', {}),
        'api': api,
        'api_candidates': api_candidates,
        'generated_at': datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    }

def _render_dual_track(dt):
    """渲染双轨制结构化数据为HTML"""
    if not dt or not dt.get('stocks'):
        return ''

    # CSS (inline style matching locked palette)
    html = '''<style>
.dt-card{margin:8px 0;background:#0D1117;border:1px solid #1C2532;border-radius:4px;overflow:hidden}
.dt-head{display:flex;justify-content:space-between;align-items:center;padding:10px 12px;border-bottom:1px solid #1C2532}
.dt-name{font-size:13px;font-weight:700}
.dt-code{font-family:'Cascadia Code','Consolas',monospace;font-size:10px;color:#0A84FF;margin-right:6px}
.dt-meta{font-family:'Cascadia Code','Consolas',monospace;font-size:9px;color:#7A8290;text-align:right}
.dt-tracks{display:flex;gap:0}
.dt-track{flex:1;padding:8px 10px;font-size:10px;line-height:1.6;border-top:1px solid rgba(28,37,50,.3)}
.dt-track-profit{background:rgba(48,209,88,.03);border-left:3px solid #30D158}
.dt-track-risk{background:rgba(255,59,48,.03);border-left:3px solid #FF3B30}
.dt-track-title{font-family:'Cascadia Code','Consolas',monospace;font-size:9px;font-weight:700;letter-spacing:1px;margin-bottom:4px}
.dt-track-profit .dt-track-title{color:#30D158}
.dt-track-risk .dt-track-title{color:#FF3B30}
.dt-row{color:#E8ECF2;margin-bottom:2px}
.dt-row .dt-label{color:#7A8290;font-size:9px;margin-right:4px}
.dt-row .dt-val{font-family:'Cascadia Code','Consolas',monospace;font-size:10px}
.dt-row .dt-val-up{color:#30D158}
.dt-row .dt-val-dn{color:#FF3B30}
.dt-row .dt-val-amber{color:#FF9F0A}
.dt-ladder{display:flex;flex-wrap:wrap;gap:3px;margin:3px 0}
.dt-ladder span{font-family:'Cascadia Code','Consolas',monospace;font-size:9px;padding:1px 5px;border-radius:2px;background:rgba(48,209,88,.08);color:#30D158;border:1px solid rgba(48,209,88,.15)}
.dt-time-section{margin:10px 0;background:#0D1117;border:1px solid #1C2532;border-radius:4px;overflow:hidden}
.dt-time-head{padding:8px 12px;background:rgba(255,159,10,.05);border-bottom:1px solid #1C2532;font-family:'Cascadia Code','Consolas',monospace;font-size:10px;font-weight:700;color:#FF9F0A;letter-spacing:1px}
.dt-time-row{display:flex;align-items:flex-start;padding:6px 12px;border-bottom:1px solid rgba(28,37,50,.2);font-size:10px;gap:8px}
.dt-time-row:last-child{border-bottom:none}
.dt-time-row.warn{background:rgba(255,59,48,.04)}
.dt-time-row.highlight{background:rgba(10,132,255,.04)}
.dt-time-win{font-family:'Cascadia Code','Consolas',monospace;font-size:9px;color:#0A84FF;min-width:65px;flex-shrink:0}
.dt-time-lbl{font-size:9px;color:#7A8290;min-width:50px;flex-shrink:0}
.dt-time-act{color:#E8ECF2;flex:1;line-height:1.4}
.dt-scenario{margin:6px 0;background:#0D1117;border:1px solid #1C2532;border-radius:4px;overflow:hidden}
.dt-sc-head{padding:7px 12px;background:rgba(10,132,255,.04);border-bottom:1px solid #1C2532;font-size:11px;font-weight:600;color:#0A84FF}
.dt-sc-body{display:flex}
.dt-sc-col{flex:1;padding:6px 10px;font-size:10px;line-height:1.5}
.dt-sc-col-profit{border-left:2px solid #30D158;color:#E8ECF2}
.dt-sc-col-risk{border-left:2px solid #FF3B30;color:#E8ECF2}
.dt-sc-label{font-family:'Cascadia Code','Consolas',monospace;font-size:8px;color:#7A8290;margin-bottom:2px;letter-spacing:.5px}
.dt-iron{margin:8px 0;padding:8px 12px;background:rgba(255,159,10,.04);border:1px solid rgba(255,159,10,.12);border-radius:4px}
.dt-iron-title{font-family:'Cascadia Code','Consolas',monospace;font-size:9px;font-weight:700;color:#FF9F0A;letter-spacing:1px;margin-bottom:4px}
.dt-iron-item{font-size:10px;color:#E8ECF2;line-height:1.6;padding-left:10px;position:relative}
.dt-iron-item:before{content:"\2022";color:#FF9F0A;position:absolute;left:0}
.dt-section-title{font-size:9px;font-weight:700;color:#7A8290;letter-spacing:1px;font-family:'Cascadia Code','Consolas',monospace;margin:12px 0 6px;padding:0 2px}
.bw-prereq{font-family:'Cascadia Code','Consolas',monospace;font-size:9px;color:#FF9F0A;margin-top:3px}
</style>'''

    # Stock cards
    for s in dt['stocks']:
        pt = s['profit_track']
        rt = s['risk_track']
        pnl_color = '#30D158' if s['pnl'] >= 0 else '#FF3B30'
        ladder_html = ''.join(f'<span>{x}</span>' for x in pt['ladder'])

        html += f'''<div class="dt-card">
  <div class="dt-head">
    <div><span class="dt-code">{s['code']}</span><span class="dt-name">{s['name']}</span></div>
    <div class="dt-meta">{s['shares']}股 | {s['weight']}% | <span style="color:{pnl_color}">{s['pnl']:+.1f}%</span></div>
  </div>
  <div class="dt-tracks">
    <div class="dt-track dt-track-profit">
      <div class="dt-track-title">▲ 盈利轨</div>
      <div class="dt-row"><span class="dt-label">三梯次</span><div class="dt-ladder">{ladder_html}</div></div>
      <div class="dt-row"><span class="dt-label">剩余</span><span class="dt-val">{pt['remaining']}</span></div>
      <div class="dt-row"><span class="dt-label">倒T</span><span class="dt-val dt-val-amber">{pt['t_trade']}</span></div>
      <div class="dt-row"><span class="dt-label">恐慌低点</span><span class="dt-val dt-val-up">{pt['panic_low']}</span></div>
    </div>
    <div class="dt-track dt-track-risk">
      <div class="dt-track-title">▼ 风控轨</div>
      <div class="dt-row"><span class="dt-label">硬止损</span><span class="dt-val dt-val-dn">{rt['hard_stop']}</span></div>
      <div class="dt-row"><span class="dt-label">趋势破位</span><span class="dt-val dt-val-dn">{rt['trend_break']}</span></div>
      <div class="dt-row"><span class="dt-label">集中度</span><span class="dt-val">{rt['concentration']}</span></div>
    </div>
  </div>
</div>'''

    # Time windows
    if dt.get('time_windows'):
        html += '<div class="dt-time-section"><div class="dt-time-head">⏱ 时间窗口执行计划</div>'
        for tw in dt['time_windows']:
            cls = ' warn' if tw.get('warn') else (' highlight' if tw.get('highlight') else '')
            html += f'<div class="dt-time-row{cls}"><span class="dt-time-win">{tw["window"]}</span><span class="dt-time-lbl">{tw["label"]}</span><span class="dt-time-act">{tw["action"]}</span></div>'
        html += '</div>'

    # Scenarios
    if dt.get('scenarios'):
        html += '<div class="dt-section-title">三情景双轨变体</div>'
        for sc in dt['scenarios']:
            html += f'''<div class="dt-scenario">
  <div class="dt-sc-head">{sc['name']}</div>
  <div class="dt-sc-body">
    <div class="dt-sc-col dt-sc-col-profit"><div class="dt-sc-label">盈利轨</div>{sc['profit']}</div>
    <div class="dt-sc-col dt-sc-col-risk"><div class="dt-sc-label">风控轨</div>{sc['risk']}</div>
  </div>
</div>'''

    # Iron rules
    if dt.get('iron_rules'):
        html += '<div class="dt-iron"><div class="dt-iron-title">铁律</div>'
        for rule in dt['iron_rules']:
            html += f'<div class="dt-iron-item">{rule}</div>'
        html += '</div>'

    # Profit targets
    if dt.get('profit_targets'):
        pt = dt['profit_targets']
        html += '<div class="dt-iron" style="border-color:rgba(48,209,88,.12);background:rgba(48,209,88,.03)">'
        html += '<div class="dt-iron-title" style="color:#30D158">收益目标</div>'
        for k, v in pt.items():
            label = {'max_amplitude':'最大振幅','t_income':'倒T收益','vs_stop_loss':'vs机械止损'}.get(k, k)
            html += f'<div class="dt-iron-item" style="color:#E8ECF2">{label}: {v}</div>'
        html += '</div>'

    return html


def build(data):
    plan = data['plan']; bw = data['buywatch']; stats = data['stats']
    plan_locked = plan.get('locked', False)
    api = data.get('api')
    dt = data.get('dual_track', {})

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

        # Short badge label from action text
        al = str(a)
        if '清' in al or al == '卖出': badge_text, row_cls, badge_cls = '清', 'sell', 'badge-sell'
        elif '减' in al: badge_text, row_cls, badge_cls = '减', 'reduce', 'badge-reduce'
        elif '买' in al: badge_text, row_cls, badge_cls = '买', 'buy', 'badge-buy'
        else: badge_text, row_cls, badge_cls = '持', 'hold', 'badge-hold'

        # Short badge + action on its own line for mobile readability
        action_line = f'<div style="font-size:10px;color:#7A8290;margin-top:2px;line-height:1.3">{a[:80]}</div>' if len(al) > 4 else ''

        if status == 'done':
            row_cls += ' executed'
            action_html = f'<span class="exec-tag done-tag">✓</span>'
        elif status == 'overridden':
            row_cls += ' overridden'
            action_html = f'<span class="exec-tag override-tag">⚠</span>'
        else:
            action_html = f'<span class="exec-btn-placeholder" onclick="execItem({item_id})">执行</span>'

        crit_border = ' critical' if is_critical else ''

        items_html += f'''<div class="item {row_cls}{crit_border}" data-id="{item_id}">
            <div class="item-left"><span class="badge {badge_cls}">{badge_text}</span></div>
            <div class="item-main">
                <div class="item-head"><span class="code">{code}</span> <span class="name">{name}</span> {action_html}</div>{action_line}
                <div class="item-meta">{reason[:100]}</div>
            </div>
            <span class="override-link" onclick="openOverride({item_id},'{code}','{name}')" title="覆盖">✎</span>
        </div>'''

    # BUY WATCH (with 建仓前提)
    bw_html = ''
    for b in bw:
        prereq = b.get('eta', '')
        notes = b.get('notes', '')
        prereq_line = f'<div class="bw-prereq">建仓前提: {prereq}</div>' if prereq and prereq != '--' else ''
        bw_html += f'''<div class="buy-item">
            <div class="bw-top"><span class="code">{b['code']}</span> {b['name']}<span class="eta">{b.get('priority','')}</span></div>
            <div class="trigger">{b.get('trigger_cond','')}</div>{prereq_line}
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

    weekday = ['周一','周二','周三','周四','周五','周六','周日'][datetime.datetime.now().weekday()]
    return f'''<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no,viewport-fit=cover">
<title>Lobster Commit</title>
<link rel="icon" type="image/png" href="./assets/logo.png">
<link rel="apple-touch-icon" href="./assets/logo.png">
<link rel="manifest" href="./manifest.json">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Commit">
<meta name="theme-color" content="#080B0F">
<style>
*{{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}}
body{{font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei','Noto Sans SC',sans-serif;background:#05080C;color:#E8ECF2;min-height:100vh;padding-bottom:140px;overflow-x:hidden}}
.header{{display:flex;justify-content:space-between;align-items:flex-start;padding:14px 16px 10px;background:rgba(5,8,12,.94);backdrop-filter:blur(12px);position:sticky;top:0;z-index:10;border-bottom:1px solid #1C2532}}
.header .header-brand{{display:flex;align-items:center;gap:8px}}
.header .header-logo{{width:28px;height:28px;border-radius:6px;object-fit:contain}}
.header .date{{font-family:'Cascadia Code','Consolas','SF Mono',monospace,monospace;font-size:15px;font-weight:700}}
.header .countdown{{font-family:'Cascadia Code','Consolas','SF Mono',monospace,monospace;font-size:10px;color:#FF9F0A}}
.state-badge{{padding:3px 10px;font-size:9px;font-family:'Cascadia Code','Consolas','SF Mono',monospace,monospace;font-weight:700;letter-spacing:1.5px;border-radius:2px}}
.state-prep{{background:rgba(110,118,136,.12);color:#7A8290;border:1px solid #1C2532}}
.state-locked{{background:rgba(255,159,10,.1);color:#FF9F0A;border:1px solid rgba(255,159,10,.2)}}
.quarantine-banner{{margin:8px 16px;padding:14px;background:rgba(255,59,48,.06);border:1px solid rgba(255,59,48,.2);border-radius:4px;text-align:center}}
.q-title{{font-family:'Cascadia Code','Consolas','SF Mono',monospace,monospace;font-size:14px;font-weight:700;color:#FF3B30;letter-spacing:2px;margin-bottom:4px}}
.q-detail{{font-size:11px;color:rgba(255,59,48,.6);margin-bottom:6px;font-family:'Cascadia Code','Consolas','SF Mono',monospace,monospace}}
.q-info{{font-size:10px;color:rgba(255,59,48,.3)}}
.lock-banner{{display:flex;align-items:center;justify-content:center;gap:8px;padding:8px 16px;margin:8px 16px;background:rgba(255,159,10,.06);border:1px solid rgba(255,159,10,.15);border-radius:4px;font-size:11px;font-family:'Cascadia Code','Consolas','SF Mono',monospace,monospace;color:#FF9F0A;letter-spacing:1px}}
.tab-bar{{display:flex;margin:8px 16px;background:#0D1117;border-radius:6px;padding:3px;border:1px solid #1C2532}}
.tab-radio{{display:none}}
.tab-radio:checked+.tab-label{{background:#141B24;color:#E8ECF2}}
.tab-label{{flex:1;text-align:center;padding:8px;font-size:11px;font-weight:600;color:#7A8290;cursor:pointer;border-radius:4px;transition:.15s;font-family:'Cascadia Code','Consolas','SF Mono',monospace,monospace;letter-spacing:.5px;display:block}}
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
.badge{{display:inline-block;font-size:9px;font-weight:700;padding:2px 8px;border-radius:2px;font-family:'Cascadia Code','Consolas','SF Mono',monospace,monospace;letter-spacing:.5px}}
.badge-sell{{background:rgba(255,59,48,.15);color:#FF3B30}}
.badge-reduce{{background:rgba(255,159,10,.12);color:#FF9F0A}}
.badge-hold{{background:rgba(48,209,88,.1);color:#30D158}}
.badge-buy{{background:rgba(10,132,255,.12);color:#0A84FF}}
.item-main{{flex:1;min-width:0}}
.item-head{{font-size:12px;font-weight:500;margin-bottom:2px}}
.item-head .code{{font-family:'Cascadia Code','Consolas','SF Mono',monospace,monospace;font-size:11px;color:#0A84FF}}
.item-head .name{{font-size:12px}}
.item-meta{{font-size:10px;color:#7A8290;line-height:1.4}}
.exec-tag{{font-size:8px;font-family:'Cascadia Code','Consolas','SF Mono',monospace,monospace;margin-left:6px}}
.done-tag{{color:#30D158}}
.override-tag{{color:#FF3B30}}
.exec-btn-placeholder{{font-size:9px;font-weight:700;padding:3px 8px;border:1px solid #30D158;border-radius:3px;color:#30D158;cursor:pointer;font-family:'Cascadia Code','Consolas','SF Mono',monospace,monospace;background:rgba(48,209,88,.08);transition:all .15s}}
.exec-btn-placeholder:active{{background:rgba(48,209,88,.2)}}
.conn-dot{{display:inline-block;width:6px;height:6px;border-radius:50%;margin-right:4px;vertical-align:middle}}
.conn-on{{background:#30D158}}.conn-off{{background:#FF3B30}}
.override-link{{font-size:9px;color:#485268;cursor:pointer;padding:2px 6px;border:1px solid transparent;font-family:'Cascadia Code','Consolas','SF Mono',monospace,monospace;flex-shrink:0;border-radius:2px}}
.override-link:hover{{color:#FF3B30;border-color:rgba(255,59,48,.3)}}

.buy-item{{padding:10px 8px;border-bottom:1px solid rgba(28,37,50,.3);background:#0D1117;border-radius:4px;margin-bottom:4px}}
.buy-item .bw-top{{display:flex;justify-content:space-between;align-items:center;font-size:12px;margin-bottom:4px}}
.buy-item .code{{font-family:'Cascadia Code','Consolas','SF Mono',monospace,monospace;font-weight:700;color:#E8ECF2}}
.buy-item .eta{{font-family:'Cascadia Code','Consolas','SF Mono',monospace,monospace;font-size:10px;font-weight:700;color:#FF9F0A}}
.buy-item .trigger{{font-size:10px;color:#7A8290;line-height:1.5}}

.stats-row{{display:flex;gap:8px;margin-bottom:12px}}
.stat-card{{flex:1;text-align:center;padding:14px 8px;background:#0D1117;border:1px solid #1C2532;border-radius:4px}}
.stat-card .v{{font-family:'Cascadia Code','Consolas','SF Mono',monospace,monospace;font-size:26px;font-weight:700}}
.stat-card .l{{font-size:9px;color:#7A8290;text-transform:uppercase;letter-spacing:.5px;margin-top:2px;font-family:'Cascadia Code','Consolas','SF Mono',monospace,monospace}}
.section-title{{font-size:10px;font-weight:700;color:#7A8290;text-transform:uppercase;letter-spacing:1px;font-family:'Cascadia Code','Consolas','SF Mono',monospace,monospace;margin-bottom:8px}}
.log-line{{font-size:9px;color:#7A8290;padding:2px 0;font-family:'Cascadia Code','Consolas','SF Mono',monospace,monospace;border-bottom:1px solid rgba(28,37,50,.2)}}
.log-time{{color:#485268;margin-right:4px}}

.float-lock{{position:fixed;bottom:20px;left:16px;right:16px;z-index:100}}
.lock-btn{{position:relative;display:block;width:100%;padding:16px;font-size:15px;font-weight:700;cursor:pointer;border:2px solid #FF9F0A;background:rgba(5,8,12,.96);color:#FF9F0A;letter-spacing:2px;font-family:'Cascadia Code','Consolas','SF Mono',monospace,monospace;text-transform:uppercase;border-radius:6px;text-align:center;backdrop-filter:blur(12px);box-shadow:0 0 40px rgba(255,159,10,.08);overflow:hidden}}
.lock-btn:active{{transform:scale(.96)}}
.lock-btn .progress{{position:absolute;bottom:0;left:0;height:4px;background:rgba(255,159,10,.8);width:0%}}
.lock-btn .sub{{font-size:9px;opacity:.5;display:block;margin-top:4px;letter-spacing:1px;font-weight:400;position:relative;z-index:1}}
.lock-btn.locked{{border-color:#485268;color:#485268;box-shadow:none;pointer-events:none}}
@keyframes lock-pulse{{0%,100%{{box-shadow:0 0 24px rgba(255,159,10,.06)}}50%{{box-shadow:0 0 48px rgba(255,159,10,.15)}}}}
.lock-btn:not(.locked){{animation:lock-pulse 3s ease-in-out infinite}}

.toast{{position:fixed;top:20px;left:50%;transform:translateX(-50%);background:#FF9F0A;color:#05080C;padding:10px 24px;border-radius:20px;font-weight:700;font-family:'Cascadia Code','Consolas','SF Mono',monospace,monospace;font-size:13px;z-index:200;opacity:0;transition:opacity .3s;pointer-events:none}}
.toast.show{{opacity:1}}
.install-banner{{display:none;align-items:center;justify-content:space-between;padding:10px 16px;margin:0 16px 8px;background:#0D1117;border:1px solid #FF9F0A;border-radius:6px;font-size:12px;color:#FF9F0A;font-family:'Cascadia Code','Consolas','SF Mono',monospace,monospace}}

/* Override modal */
.modal-overlay{{position:fixed;inset:0;background:rgba(5,8,12,.95);z-index:150;display:none;align-items:center;justify-content:center}}
.modal-overlay.active{{display:flex}}
.modal{{background:#0D1117;border:1px solid #1C2532;padding:20px;margin:16px;border-radius:6px;max-width:340px}}
.modal h3{{font-size:14px;font-weight:700;color:#FF3B30;font-family:'Cascadia Code','Consolas','SF Mono',monospace,monospace;margin-bottom:8px}}
.modal .tags{{display:flex;gap:6px;flex-wrap:wrap;margin:12px 0}}
.modal .tag{{padding:6px 14px;border-radius:14px;font-size:11px;cursor:pointer;border:1px solid #1C2532;background:#05080C;color:#7A8290;font-family:'Cascadia Code','Consolas','SF Mono',monospace,monospace;transition:.15s}}
.modal .tag.selected{{border-color:#FF3B30;background:rgba(255,59,48,.1);color:#FF3B30}}
.modal .btn-row{{display:flex;gap:8px;margin-top:12px}}
.modal .btn-confirm{{flex:1;padding:12px;border-radius:4px;font-size:12px;font-weight:700;cursor:pointer;border:none;background:#FF3B30;color:#fff;opacity:.3;pointer-events:none;font-family:'Cascadia Code','Consolas','SF Mono',monospace,monospace}}
.modal .btn-confirm.ready{{opacity:1;pointer-events:auto}}
.modal .btn-cancel{{flex:1;padding:12px;border-radius:4px;font-size:12px;cursor:pointer;border:1px solid #1C2532;background:transparent;color:#7A8290;font-family:'Cascadia Code','Consolas','SF Mono',monospace,monospace}}
</style></head>
<body onload="countdownTick();setInterval(countdownTick,60000)">
<div class="header">
    <div class="header-brand"><img class="header-logo" src="./assets/logo.png" alt="L"><div><div class="date">{plan["date"]} · {weekday}</div><div class="countdown" id="countdown">距离开盘 {countdown_text}</div></div></div></div>
    <div class="state-badge {state_cls}" id="stateBadge">{state_label}</div>
</div>

<div id="connStatus" style="text-align:center;padding:4px;font-size:9px;font-family:'Cascadia Code','Consolas','SF Mono',monospace,monospace"></div>
<div style="text-align:center;padding:4px;font-size:8px;font-family:monospace"><span id=\"verTag\" style=\"color:#485268\">v?</span> · <a href=\"javascript:navigator.serviceWorker.getRegistrations().then(r=>r.forEach(x=>x.unregister()));caches.keys().then(k=>k.forEach(x=>caches.delete(x)));location.reload();\" style=\"color:#FF3B30;text-decoration:none\">硬核重置</a></div>
{offline_note}
{q_html}
<!-- banner removed per UI spec §十三 -->

<input type="radio" class="tab-radio" name="tab" id="tr0" checked>
<input type="radio" class="tab-radio" name="tab" id="tr1">
<input type="radio" class="tab-radio" name="tab" id="tr2">
<div class="tab-bar">
    <label class="tab-label" for="tr0">📊 双轨</label>
    <label class="tab-label" for="tr1">🎯 候选</label>
    <label class="tab-label" for="tr2">📊 状态</label>
</div>

<div class="tab-panel" id="tp0">
    {_render_dual_track(dt) if dt else ''}
    {'<div class="dt-section-title">执行项</div>' if dt and items_html else ''}
    {items_html if items_html else '<div style="text-align:center;padding:40px 20px"><img src="./assets/empty.png" style="width:120px;height:auto;opacity:.4;margin-bottom:12px"><div style="color:#7A8290;font-size:12px;font-family:monospace">暂无计划项</div></div>'}
</div>
<div class="tab-panel" id="tp1">
    {bw_html if bw else '<div style="text-align:center;padding:40px 20px"><img src="./assets/empty.png" style="width:120px;height:auto;opacity:.4;margin-bottom:12px"><div style="color:#7A8290;font-size:12px;font-family:monospace">等待选股</div></div>'}
</div>
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

<div class="toast" id="quarantineToast" style="position:fixed;inset:0;background:rgba(5,8,12,.98);z-index:250;display:none;flex-direction:column;align-items:center;justify-content:center;font-family:'Cascadia Code','Consolas','SF Mono',monospace,monospace">
    <div style="font-size:18px;color:#FF3B30;font-weight:700;letter-spacing:3px;margin-bottom:8px">QUARANTINE</div>
    <div style="font-size:48px;font-weight:700;color:#FF3B30" id="qCountdown">02:00:00</div>
    <div style="font-size:10px;color:rgba(255,59,48,.3);margin:8px 0 24px;letter-spacing:2px">计划外操作已冻结</div>
    <button onclick="closeQuarantine()" style="background:none;border:1px solid #485268;color:#7A8290;padding:8px 24px;border-radius:4px;font-size:12px;font-family:'Cascadia Code','Consolas','SF Mono',monospace,monospace">关闭</button>
</div>

<script>
var API = '{api or ""}';
var API_CANDIDATES = {json.dumps(data.get('api_candidates', []))};
var locked = {str(plan_locked).lower()};
var overrideItemId = null, selectedTag = '';
var qTimer = null, isOnline = false;
var localState = {{}};
try {{ localState = JSON.parse(localStorage.getItem('commit_state') || '{{"locked":false,"executed":[],"overridden":[]}}'); }} catch(e) {{}};
// 锁以服务器为准，不用 localStorage 覆盖

function saveState() {{ localStorage.setItem('commit_state', JSON.stringify(localState)); }}
function isExecuted(id) {{ return localState.executed.indexOf(id) !== -1; }}
function isOverridden(id) {{ return localState.overridden.indexOf(id) !== -1; }}

async function tryApi(url) {{
    try {{ var r = await fetch(url + '/api/state'); if (r.ok) return url; }} catch(e) {{}}
    return null;
}}
async function discoverApi() {{
    // Try current API first if set
    if (API) {{ var ok = await tryApi(API); if (ok) return true; }}
    // Try last known good API
    var lastApi = localStorage.getItem('last_api');
    if (lastApi) {{ var ok = await tryApi(lastApi); if (ok) {{ API = ok; return true; }} }}
    // Try all candidates
    for (var i = 0; i < API_CANDIDATES.length; i++) {{
        var ok = await tryApi(API_CANDIDATES[i]);
        if (ok) {{ API = ok; localStorage.setItem('last_api', API); return true; }}
    }}
    return false;
}}
async function checkConn() {{
    var el = document.getElementById('connStatus');
    if (!API) {{
        var found = await discoverApi();
        if (found) {{
            if (el) el.innerHTML = '<span class="conn-dot conn-on"></span>已连接';
            syncToServer();
        }} else {{
            isOnline = false;
            if (el) el.innerHTML = '<span class="conn-dot conn-off"></span>离线 · 缓存数据';
        }}
        return;
    }}
    try {{ var r = await fetch(API + '/api/state', {{method:'GET'}}); isOnline = r.ok; }} catch(e) {{ isOnline = false; }}
    if (!isOnline) {{
        var found = await discoverApi();
        if (found) isOnline = true;
    }}
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
    // 锁不由客户端同步 — 只有用户长按封印按钮才能锁
	    // (localState.locked) sync removed per user request
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
    b.className = 'install-banner'; b.style.display = 'flex'; b.innerHTML = '<span>📱 安装到桌面</span><button onclick=\"installApp()\" style=\"background:#FF9F0A;color:#05080C;border:none;padding:6px 14px;border-radius:4px;font-weight:700;font-family:Consolas,monospace;cursor:pointer\">安装</button>';
    document.body.insertBefore(b, document.body.firstChild);
}});
function installApp() {{
    if (deferredPrompt){{ deferredPrompt.prompt(); deferredPrompt.userChoice.then(function(r){{ }}); }}
}}

if ('serviceWorker' in navigator) {{ navigator.serviceWorker.register('./sw.js?t=11'); }}
document.getElementById('verTag').textContent = 'v11';
// Load quarantine state
(function() {{
    if (API) {{
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
