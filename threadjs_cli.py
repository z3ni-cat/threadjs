#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ThreadJS CLI v2 — Threads auto komen/like/follow, jalan di Terminal PC & Termux.

Cookie tersimpan LOKAL di device-mu (~/.threadjs/session.json, chmod 600) —
tidak dikirim ke server manapun selain threads.com sendiri.

Dependensi: python3 + requests  →  pip install requests
Mulai: python threadjs_cli.py          (menu interaktif)
       python threadjs_cli.py login    (input cookie)
       python threadjs_cli.py auto keyword "voucher shopee" --reply --max 10
"""
import argparse
import json
import os
import random
import re
import sys
import time

try:
    import requests
except ImportError:
    print("\033[91m[✗] requests belum terpasang. Jalankan: pip install requests\033[0m")
    sys.exit(1)

# ── konstanta engine ──────────────────────────────────────────────────────
APP_ID = '238260118697367'
GQL_URL = 'https://www.threads.com/api/graphql'
BASE = 'https://www.threads.com'
UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')

DOC = {
    'userinfo':    '23996318473300828',
    'userthreads': '6232751443445612',
    'keyword':     '9510039600775399',
    'followers':   '7607196049278053',
}

DIR = os.path.join(os.path.expanduser('~'), '.threadjs')
SESS_F = os.path.join(DIR, 'session.json')
CFG_F = os.path.join(DIR, 'config.json')
CFG_DEFAULT = {'delay_reply': 90, 'delay_like': 45, 'delay_follow': 90, 'max_actions': 20}

# ── tampilan ──────────────────────────────────────────────────────────────
class C:
    g = '\033[92m'; r = '\033[91m'; c = '\033[96m'; y = '\033[93m'
    d = '\033[2m'; b = '\033[1m'; x = '\033[0m'
    @classmethod
    def off(cls):
        if not sys.stdout.isatty():
            for k in ('g', 'r', 'c', 'y', 'd', 'b', 'x'):
                setattr(cls, k, '')

C.off()

def say(msg, color=''):
    print(f"{color}{msg}{C.x}", flush=True)

def info(m): say(f"{C.c}[i]{C.x} {m}")
def ok(m):   say(f"{C.g}[✓]{C.x} {m}")
def err(m):  say(f"{C.r}[✗]{C.x} {m}")
def warn(m): say(f"{C.y}[!]{C.x} {m}")


class TJSException(Exception):
    pass


# ── sesi & config ─────────────────────────────────────────────────────────
def load_sess():
    if not os.path.isfile(SESS_F):
        return None
    try:
        with open(SESS_F) as f:
            j = json.load(f)
        return j if j.get('cookie') else None
    except Exception:
        return None


def save_sess(cookie, meta):
    os.makedirs(DIR, exist_ok=True)
    with open(SESS_F, 'w') as f:
        json.dump({'cookie': cookie, 'saved_at': int(time.time()), **meta}, f)
    os.chmod(SESS_F, 0o600)


def clear_sess():
    if os.path.isfile(SESS_F):
        os.remove(SESS_F)


def load_cfg():
    try:
        with open(CFG_F) as f:
            j = json.load(f)
    except Exception:
        j = {}
    out = dict(CFG_DEFAULT)
    out.update({k: v for k, v in j.items() if k in CFG_DEFAULT})
    return out


def save_cfg(cfg):
    os.makedirs(DIR, exist_ok=True)
    with open(CFG_F, 'w') as f:
        json.dump(cfg, f, indent=2)


# ── HTTP engine ───────────────────────────────────────────────────────────
def base_headers(cookie):
    return {
        'user-agent': UA,
        'x-ig-app-id': APP_ID,
        'x-requested-with': 'XMLHttpRequest',
        'sec-fetch-site': 'same-origin',
        'cookie': cookie,
    }


def gql(cookie, doc_id, variables):
    r = requests.post(
        GQL_URL,
        data={
            'variables': json.dumps(variables),
            'doc_id': doc_id,
            'server_timestamps': 'true',
        },
        headers={**base_headers(cookie),
                 'content-type': 'application/x-www-form-urlencoded',
                 'x-fb-friendly-name': 'ThreadJS'},
        timeout=25,
    )
    if r.status_code in (401, 403):
        raise TJSException('SESSION MATI — cookie expired/invalid, login ulang')
    if r.status_code == 429:
        raise TJSException('RATE-LIMIT Threads — istirahat 10-15 menit')
    if r.history or r.status_code in (301, 302):
        raise TJSException('Cookie DITOLAK (redirect login) — sessionid kurang. '
                           'Export lengkap via Cookie-Editor.')
    if r.status_code != 200:
        raise TJSException(f'HTTP {r.status_code} dari Threads')
    j = r.json()
    if j.get('errors'):
        m = j['errors'][0].get('message') or j['errors'][0].get('summary') or 'graphql error'
        raise TJSException(f'GraphQL: {m}')
    return j.get('data') or {}


def rest(cookie, method, path, fields=None):
    r = requests.request(
        method, BASE + path,
        data=fields,
        headers=base_headers(cookie),
        timeout=25,
    )
    if r.status_code in (401, 403):
        raise TJSException('SESSION MATI — cookie expired/invalid')
    if r.status_code == 429:
        raise TJSException('RATE-LIMIT — aksi terlalu cepat, jeda dulu')
    if r.history or r.status_code in (301, 302):
        raise TJSException('Sesi ditolak (redirect login) — login ulang')
    if r.status_code >= 400:
        raise TJSException(f'HTTP {r.status_code} dari Threads')
    try:
        return r.json()
    except Exception:
        return {'raw': r.text}


# ── normalisasi cookie (JSON Cookie-Editor ATAU header string) ────────────
def normalize_cookie(raw):
    raw = raw.strip()
    if raw.startswith('[') or raw.startswith('{'):
        try:
            j = json.loads(raw)
        except Exception:
            return raw
        pairs = []
        if isinstance(j, list):
            for c in j:
                if c.get('name'):
                    pairs.append(f"{c['name']}={c.get('value', '')}")
        elif isinstance(j, dict):
            for k, v in j.items():
                if isinstance(v, (str, int)):
                    pairs.append(f'{k}={v}')
        return '; '.join(pairs)
    return raw


def my_uid(cookie):
    m = re.search(r'ds_user_id=(\d+)', cookie)
    return m.group(1) if m else ''


# ── walkers ───────────────────────────────────────────────────────────────
def walk_items(node, out=None, depth=0):
    if out is None:
        out = []
    if not isinstance(node, dict) or depth > 14:
        return out
    for k, v in node.items():
        if k == 'thread_items' and isinstance(v, list):
            out.extend(v)
        walk_items(v, out, depth + 1)
    return out


def item_info(t):
    p = t.get('post') or {}
    if not p.get('pk'):
        return None
    u = p.get('user') or {}
    return {
        'pk': str(p['pk']),
        'code': p.get('code', ''),
        'url': p.get('url') or f"https://www.threads.com/@x/post/{p.get('code', '')}",
        'username': u.get('username', ''),
        'userId': str(u.get('pk', '')) if u.get('pk') else '',
        'text': (p.get('caption') or {}).get('text', '')[:120],
        'likeCount': int(p.get('like_count') or 0),
        'isReply': bool(t.get('reply_to_author')),
    }


def uid_from(cookie, username):
    r = requests.get(f'{BASE}/@{username}', headers=base_headers(cookie), timeout=20,
                     allow_redirects=True)
    m = re.search(r'"user_id":"(\d{10,20})"', r.text)
    if m:
        return m.group(1)
    # fallback: cari lewat keyword search
    data = gql(cookie, DOC['keyword'], {'query': username})
    for t in walk_items(data):
        i = item_info(t)
        if i and i['username'].lower() == username.lower():
            return i['userId']
    raise TJSException(f'User @{username} tidak ketemu')


# ── aksi ──────────────────────────────────────────────────────────────────
def act_like(sess, pk):
    uid = my_uid(sess['cookie'])
    if not uid:
        raise TJSException('ds_user_id tidak ada di cookie — login ulang')
    return rest(sess['cookie'], 'POST', f'/api/v1/media/{pk}_{uid}/like/')


def act_reply(sess, pk, text):
    if len(text) > 480:
        raise TJSException('komentar > 480 karakter')
    return rest(sess['cookie'], 'POST', '/api/v1/text_app/reply/',
                {'text': text, 'media_id': pk, 'direct_reply': '1'})


def act_follow(sess, uid):
    return rest(sess['cookie'], 'POST', f'/api/v1/friendships/create/{uid}/')


# ── spinner komentar {a|b} ────────────────────────────────────────────────
def spin(t):
    for _ in range(3):
        t = re.sub(r'\{([^{}]+)\}',
                   lambda m: random.choice(m.group(1).split('|')).strip(), t)
    return t


# ── ambil data ────────────────────────────────────────────────────────────
def fetch_search(sess, kw, mx):
    data = gql(sess['cookie'], DOC['keyword'], {'query': kw})
    posts = []
    for t in walk_items(data):
        i = item_info(t)
        if i and not i['isReply']:
            posts.append(i)
    return posts[:mx]


def fetch_user_posts(sess, username, mx):
    uid = uid_from(sess['cookie'], username)
    data = gql(sess['cookie'], DOC['userthreads'], {'userID': uid})
    posts = []
    for t in walk_items(data):
        i = item_info(t)
        if i and not i['isReply']:
            posts.append(i)
    return posts[:mx]


def fetch_followers(sess, username, mx):
    uid = uid_from(sess['cookie'], username)
    data = gql(sess['cookie'], DOC['followers'],
               {'id': uid, 'surface': 'profile', 'page_size': mx})
    users, seen = [], set()
    stack = [data]
    while stack:
        cur = stack.pop()
        if not isinstance(cur, dict):
            continue
        for v in cur.values():
            if isinstance(v, dict):
                if v.get('username') and v.get('pk') and v['username'] not in seen:
                    seen.add(v['username'])
                    users.append({'pk': str(v['pk']), 'username': v['username']})
                stack.append(v)
            elif isinstance(v, list):
                stack.extend(x for x in v if isinstance(x, dict))
    return users[:mx]


# ── batch runner ──────────────────────────────────────────────────────────
def run_batch(items, mode, comments, delay, label, cfg):
    stats = {'ok': 0, 'fail': 0}
    total = min(len(items), cfg['max_actions'])
    say(f"\n{C.b}▶ Target: {label} — {total} aksi, delay ±{delay}s{C.x}")
    warn('Ctrl+C kapanpun utk berhenti (aman, selesai dgn rapi)')
    try:
        for n, it in enumerate(items[:total], 1):
            tag = it['username'] if 'username' in it else it.get('pk', '?')
            try:
                if mode == 'reply':
                    c = spin(random.choice(comments)) if comments else 'Nice!'
                    act_reply(SESS, it['pk'], c)
                    say(f"  {C.d}[{n}/{total}]{C.x} 💬 @{tag}: \"{c}\" {C.g}✓{C.x}")
                elif mode == 'like':
                    act_like(SESS, it['pk'])
                    say(f"  {C.d}[{n}/{total}]{C.x} ❤️  @{tag} {C.g}✓{C.x}")
                elif mode == 'follow':
                    act_follow(SESS, it['pk'])
                    say(f"  {C.d}[{n}/{total}]{C.x} ➕ @{it.get('username', it['pk'])} {C.g}✓{C.x}")
                stats['ok'] += 1
            except KeyboardInterrupt:
                raise
            except TJSException as e:
                stats['fail'] += 1
                say(f"  {C.d}[{n}/{total}]{C.x} ✗ @{tag}: {e}", C.r)
                if re.search(r'SESSION|RATE-LIMIT|ditolak', str(e), re.I):
                    err('dihentikan — ' + str(e))
                    break
            except Exception as e:
                stats['fail'] += 1
                say(f"  {C.d}[{n}/{total}]{C.x} ✗ @{tag}: {e}", C.r)
            # jeda humanisasi ±30%:
            if n < total:
                time.sleep(max(15, delay * random.uniform(0.7, 1.3)))
    except KeyboardInterrupt:
        print()
        warn('STOP diminta — berhenti dgn rapi')
    say(f"\n{C.b}■ SELESI{C.x} — ok: {C.g}{stats['ok']}{C.x}, gagal: {C.r}{stats['fail']}{C.x}")
    return stats


SESS = None

# ── perintah CLI ──────────────────────────────────────────────────────────
def cmd_login(_):
    say(f"\n{C.b}🍪 Login ThreadJS{C.x}")
    say(f"{C.d}Ambil cookie: buka threads.com (sudah login) → ekstensi Cookie-Editor →")
    say(f"{C.d}Export JSON ATAU Header String → paste di bawah.{C.x}")
    say(f"{C.d}Cookie tersimpan LOKAL ({SESS_F}), tidak dibagikan.{C.x}\n")
    raw = input('Paste cookie > ').strip()
    cookie = normalize_cookie(raw)
    if len(cookie) < 40 or 'ds_user_id' not in cookie:
        return err('Cookie tidak lengkap (ds_user_id tidak ketemu)')
    try:
        uid = re.search(r'ds_user_id=(\d+)', cookie).group(1)
        data = gql(cookie, DOC['userinfo'], {'userID': uid})
        user = (data.get('userData') or {}).get('user')
        if not user:
            return err('Cookie ditolak Threads — sessionid kurang/expired')
        save_sess(cookie, {'username': user.get('username', ''), 'pk': str(user.get('pk') or uid)})
        ok(f"Login OK — @{user.get('username')} "
           f"({user.get('follower_count', '?')} followers)")
        say(f"{C.d}Sesi tersimpan di {SESS_F}{C.x}")
    except TJSException as e:
        err(str(e))


def cmd_whoami(_):
    s = load_sess()
    if not s:
        return err('Belum login — jalankan: python threadjs_cli.py login')
    try:
        uid = my_uid(s['cookie'])
        data = gql(s['cookie'], DOC['userinfo'], {'userID': uid})
        u = (data.get('userData') or {}).get('user')
        if not u:
            return err('Sesi mati — login ulang')
        ok(f"@{u.get('username')} — {u.get('full_name', '')} — "
           f"{u.get('follower_count', '?')} followers — simpan {time.strftime('%d %b %H:%M', time.localtime(s['saved_at']))}")
    except TJSException as e:
        err(str(e))


def cmd_logout(_):
    clear_sess()
    ok('Cookie dihapus dari device')


def print_posts(posts):
    if not posts:
        return warn('0 post ketemu')
    for n, p in enumerate(posts, 1):
        say(f"  {C.d}{n:>2}.{C.x} @{C.c}{p['username']}{C.x} ❤{p['likeCount']} — "
            f"{p['text'][:70].replace(chr(10), ' ')}")
        say(f"       {C.d}pk: {p['pk']}  {p['url']}{C.x}")


def cmd_search(a):
    s = load_sess()
    if not s:
        return err('Belum login dulu')
    try:
        print_posts(fetch_search(s, a.keyword, min(a.max, 40)))
    except TJSException as e:
        err(str(e))


def cmd_user(a):
    s = load_sess()
    if not s:
        return err('Belum login dulu')
    try:
        print_posts(fetch_user_posts(s, a.username.lstrip('@'), min(a.max, 40)))
    except TJSException as e:
        err(str(e))


def cmd_single(a):
    s = load_sess()
    if not s:
        return err('Belum login dulu')
    try:
        if a.action == 'like':
            act_like(s, a.id)
            ok(f'like {a.id} ✓')
        elif a.action == 'follow':
            uid = a.id if a.id.isdigit() else uid_from(s['cookie'], a.id.lstrip('@'))
            act_follow(s, uid)
            ok(f'follow {uid} ✓')
        elif a.action == 'reply':
            if not a.text:
                return err('reply butuh --text "isi komentar"')
            act_reply(s, a.id, a.text)
            ok(f'reply {a.id} ✓')
    except TJSException as e:
        err(str(e))


def do_auto(kind, target, opts, cfg):
    global SESS
    SESS = load_sess()
    if not SESS:
        return err('Belum login dulu')
    mode = opts.mode
    if kind == 'keyword':
        try:
            items = fetch_search(SESS, target, min(opts.max, 40))
        except TJSException as e:
            return err(str(e))
        label = f'keyword "{target}"'
    elif kind == 'user':
        try:
            items = fetch_user_posts(SESS, target.lstrip('@'), min(opts.max, 40))
        except TJSException as e:
            return err(str(e))
        label = f'post @{target.lstrip("@")}'
    else:  # followers
        try:
            items = fetch_followers(SESS, target.lstrip('@'), min(opts.max, 40))
        except TJSException as e:
            return err(str(e))
        label = f'followers @{target.lstrip("@")}'
    if not items:
        return warn('target kosong — selesai')
    comments = [c.strip() for c in (opts.comments or '').split('|') if c.strip()]
    delay = opts.delay or cfg.get(f'delay_{mode}', 60)
    run_batch(items, mode, comments, delay, label, cfg)


def cmd_auto(a):
    cfg = load_cfg()
    do_auto(a.kind, a.target, a, cfg)


# ── menu interaktif (mode default, enak di Termux) ────────────────────────
def ask_int(prompt, default, lo, hi):
    raw = input(prompt).strip()
    if not raw:
        return default
    try:
        return max(lo, min(hi, int(raw)))
    except ValueError:
        return default


def menu():
    cfg = load_cfg()
    s = load_sess()
    print(f"\n{C.b}╔════════════════════════════════════╗")
    print(f"║   🧵 ThreadJS CLI v2 — Threads auto   ║")
    print(f"╚════════════════════════════════════╝{C.x}")
    if s:
        ok(f"sesi: @{s.get('username', '?')}")
    else:
        warn('belum login')
    print(f"""
  {C.b}1.{C.x} 🍪 Login / ganti cookie
  {C.b}2.{C.x} 👤 Cek sesi
  {C.b}3.{C.x} 🔎 Auto by KEYWORD   (reply/like)
  {C.b}4.{C.x} 🎯 Auto by USER      (reply/like)
  {C.b}5.{C.x} ➕ Auto FOLLOW followers user
  {C.b}6.{C.x} ⚙️  Pengaturan delay (sekarang: reply {cfg['delay_reply']}s, like {cfg['delay_like']}s, follow {cfg['delay_follow']}s)
  {C.b}0.{C.x} Keluar""")
    p = input(f'{C.b}pilih>{C.x} ').strip()
    if p == '1':
        cmd_login(None)
    elif p == '2':
        cmd_whoami(None)
    elif p in ('3', '4'):
        kw = input('Keyword > ' if p == '3' else 'Username target > ').strip()
        if not kw:
            return warn('kosong')
        m = input('Aksi [reply/like] (reply) > ').strip().lower() or 'reply'
        if m not in ('reply', 'like'):
            m = 'reply'
        cmt = ''
        if m == 'reply':
            cmt = input('Komentar {a|b}=random ("Mantap!|Keren 🔥") > ').strip() or 'Mantap!|Keren 🔥|Nice banget 👏'
        mx = ask_int('Jumlah maksimal (10) > ', 10, 1, 40)
        dl = ask_int(f'Delay detik ({cfg["delay_reply"] if m=="reply" else cfg["delay_like"]}) > ',
                     cfg['delay_reply'] if m == 'reply' else cfg['delay_like'], 30, 600)
        do_auto('keyword' if p == '3' else 'user', kw,
                argparse.Namespace(mode=m, max=mx, delay=dl, comments=cmt), cfg)
    elif p == '5':
        un = input('Username target > ').strip()
        if not un:
            return warn('kosong')
        mx = ask_int('Jumlah follow maksimal (10) > ', 10, 1, 40)
        dl = ask_int(f'Delay detik ({cfg["delay_follow"]}) > ', cfg['delay_follow'], 30, 600)
        do_auto('followers', un,
                argparse.Namespace(mode='follow', max=mx, delay=dl, comments=''), cfg)
    elif p == '6':
        cfg['delay_reply'] = ask_int(f'Delay reply ({cfg["delay_reply"]}) > ', cfg['delay_reply'], 30, 600)
        cfg['delay_like'] = ask_int(f'Delay like ({cfg["delay_like"]}) > ', cfg['delay_like'], 20, 600)
        cfg['delay_follow'] = ask_int(f'Delay follow ({cfg["delay_follow"]}) > ', cfg['delay_follow'], 30, 600)
        save_cfg(cfg)
        ok('pengaturan disimpan')
    elif p == '0':
        say('dadah 👋')
        sys.exit(0)


# ── argparse ──────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) <= 1:
        try:
            while True:
                menu()
        except (KeyboardInterrupt, EOFError):
            print()
            say('dadah 👋')
        return
    ap = argparse.ArgumentParser(prog='threadjs', description='ThreadJS CLI v2 — Threads auto engine')
    sub = ap.add_subparsers(dest='cmd')

    sub.add_parser('login', help='input/ubah cookie (lokal, chmod 600)')
    sub.add_parser('whoami', help='cek sesi aktif')
    sub.add_parser('logout', help='hapus cookie dari device')

    s = sub.add_parser('search', help='lihat post per keyword')
    s.add_argument('keyword')
    s.add_argument('--max', type=int, default=10)

    s = sub.add_parser('user', help='lihat post milik user')
    s.add_argument('username')
    s.add_argument('--max', type=int, default=10)

    s = sub.add_parser('do', help='aksi tunggal: like|reply|follow')
    s.add_argument('action', choices=['like', 'reply', 'follow'])
    s.add_argument('id', help='pk post (like/reply) atau username/uid (follow)')
    s.add_argument('--text', default='', help='isi komentar utk reply')

    s = sub.add_parser('auto', help='mode batch: auto keyword|user|followers <target>')
    s.add_argument('kind', choices=['keyword', 'user', 'followers'])
    s.add_argument('target')
    s.add_argument('--mode', choices=['reply', 'like', 'follow'], default='reply')
    s.add_argument('--comments', default='', help='"a|b|c" variasi komentar (reply)')
    s.add_argument('--max', type=int, default=10)
    s.add_argument('--delay', type=int, default=0, help='0 = pakai default config')

    a = ap.parse_args()
    fn = {'login': cmd_login, 'whoami': cmd_whoami, 'logout': cmd_logout,
          'search': cmd_search, 'user': cmd_user, 'do': cmd_single,
          'auto': cmd_auto}.get(a.cmd)
    if fn:
        fn(a)


if __name__ == '__main__':
    main()
