<div align="center">

# 🎬 Ani-Me Downloader

**A sleek, modern anime downloader & streamer for the desktop.**

Browse, grab, and binge — all from one beautiful Fluent UI.

[![License: GPLv3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-green.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)]()

[Disclaimer](disclaimer.md) · [Report Bug](https://github.com/anirbanmajumder0/Ani-Me-Downloader/issues/new?template=bug_report.md) · [Request Feature](https://github.com/anirbanmajumder0/Ani-Me-Downloader/issues/new?template=feature_request.md)

</div>

---

## ✨ Features

- 🔍 **Search & browse** anime with metadata, posters, and synopses
- ⬇️ **Built-in torrent engine** powered by `libtorrent` — no external client needed
- 📺 **Auto-track airing series** — new episodes grabbed as they drop
- 🎨 **Fluent UI** with smooth animations and modern look
- 🗂️ **Library management** — organize, rename, and clean up downloads
- ⚡ **Lightweight** — single app, no bloat

---

## 🚀 Quick Start

### Requirements

- **Python 3.10+** ([download](https://python.org/downloads))
- **Git**
- Platform: Windows, Linux, or macOS

### Install & Run

```bash
# 1. Clone
git clone https://github.com/anirbanmajumder0/Ani-Me-Downloader
cd Ani-Me-Downloader

# 2. Install Briefcase (build tool)
pip install -r requirements.txt

# 3. Run in dev mode
briefcase dev
```

That's it. 🎉

---

## 📦 Building a Native App

Want a real installable app instead of running from source?

```bash
briefcase create     # scaffold the app
briefcase build      # compile
briefcase run        # launch packaged build
briefcase package    # produce installer (.msi / .deb / .dmg / etc.)
```

Output lands in `dist/`.

---

## 🛠️ Tech Stack

| Layer | Tool |
|-------|------|
| GUI | PyQt5 + [PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets) |
| Torrents | libtorrent 2.0 |
| Scraping | requests + BeautifulSoup4 |
| Packaging | [BeeWare Briefcase](https://briefcase.readthedocs.io/) |

---

## 🐛 Troubleshooting

- **`libtorrent` install fails on Linux/macOS?** Use system package: `sudo pacman -S libtorrent-rasterbar` (Arch), `brew install libtorrent-rasterbar` (macOS), or `apt install python3-libtorrent` (Debian).
- **PyQt errors on Wayland?** Run with `QT_QPA_PLATFORM=xcb briefcase dev`.
- **App tested mainly on Windows** — Linux/macOS may have rough edges. PRs welcome!

---

## 🤝 Contributing

Contributions are very welcome. Bug fix, feature, doc tweak — all good.

1. Fork the repo
2. Create a feature branch
3. Open a PR

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

---

## 📜 License

[GPLv3](LICENSE) — free as in freedom.

---

<div align="center">

Made with ❤️ by [Anirban Majumder](https://github.com/anirbanmajumder0) and contributors.

⭐ **Star the repo if you find it useful!**

</div>
