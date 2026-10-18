# 🧵 ThreadJS — Threads Auto Komen / Like / Follow

Auto reply, like, dan follow untuk **Threads** (threads.com) langsung dari
terminal — jalan di PC, laptop, dan **Termux** (Android). Tanpa browser,
tanpa bookmarklet, cookie tersimpan **100% lokal** di device-mu.

> ⚠️ Saat ini Threads API resmi tidak menyediakan endpoint auto-engage untuk
> third-party, jadi tool ini memakai endpoint internal web Threads
> (sama seperti yang dipakai browser kamu saat login). Gunakan dengan bijak
> dan tanggung risiko sendiri.

## ✨ Fitur

- 🔎 **Auto by keyword** — reply/like semua post per keyword pencarian
- 🎯 **Auto by user** — reply/like post milik user tertentu
- ➕ **Auto follow followers** — follow followers-nya user target
- 💬 Spinner komentar `{a|b|c}` — variasi komentar random biar tidak spammy
- 🛡 Humanisasi: delay acak ±30%, max aksi per run, auto-stop saat rate-limit
- 🍪 Login via cookies (JSON Cookie-Editor ATAU header string)
- 📱 Mode menu interaktif untuk Termux + mode CLI langsung untuk PC

## 📦 Install

### Termux (Android)
```bash
pkg update && pkg install python -y
pip install requests
curl -O https://raw.githubusercontent.com/z3ni-cat/threadjs/main/threadjs_cli.py
python threadjs_cli.py
```

### PC / Laptop
```bash
pip install requests
curl -O https://raw.githubusercontent.com/z3ni-cat/threadjs/main/threadjs_cli.py
python threadjs_cli.py
```

## 🍪 Cara Login

1. Buka **threads.com** di browser, pastikan sudah login
2. Pasang ekstensi **Cookie-Editor** (Chrome / Firefox / Edge; di HP pakai Kiwi Browser)
3. Klik ikon Cookie-Editor → **Export** → **Export JSON** (atau Header String)
4. Jalankan `python threadjs_cli.py login` → paste cookie → Enter

Cookie disimpan di `~/.threadjs/session.json` (chmod 600) dan **hanya
digunakan untuk berkomunikasi dengan threads.com** — tidak dikirim ke server
manapun.

## 🚀 Contoh Pakai

```bash
# Menu interaktif (rekomendasi)
python threadjs_cli.py

# Cek sesi aktif
python threadjs_cli.py whoami

# Lihat post per keyword
python threadjs_cli.py search "voucher shopee"

# Auto-reply post per keyword (variasi komentar random)
python threadjs_cli.py auto keyword "promo diskon" --mode reply --max 10 \
    --comments "Mantap!|Keren 🔥|Nice banget"

# Auto-like post milik user
python threadjs_cli.py auto user "username_target" --mode like --max 10

# Follow followers-nya user (delay 90s biar aman)
python threadjs_cli.py auto followers "username_target" --max 10 --delay 90
```

## ⚙️ Pengaturan Delay (PENTING biar akun awet)

| Aksi   | Default | Rekomendasi |
|--------|---------|-------------|
| Reply  | 90 dtk  | jangan turun dari 60 dtk |
| Like   | 45 dtk  | jangan turun dari 20 dtk |
| Follow | 90 dtk  | jangan turun dari 60 dtk |

Delay di-randomize ±30% per aksi (misal set 90 → jalan 63-117 dtk) supaya
pola tidak robotik. Kalau muncul `RATE-LIMIT`, istirahatkan 10-15 menit.

## 🛡 Peringatan

- Ini tool unofficial — Threads bisa mengubah endpoint-nya kapan saja
- Akun baru sebaiknya jangan langsung agresif (mulai pelan dulu)
- Cookie = kunci penuh akunmu. **Jangan pernah** dibagikan ke siapapun,
  termasuk dikirim lewat chat/messenger
- Segala risiko pemakaian (suspension, limitation) ditanggung user

## 📄 License

MIT — lihat [LICENSE](LICENSE)
