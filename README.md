# Duplicate File Scanner

A small desktop app that finds files saved under the **same name in equivalent formats** (like `photo_1.jpg` and `photo_1.png`), groups them, and lets you review and delete the copies you don't want.

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![Platforms](https://img.shields.io/badge/platform-Linux%20%7C%20Windows-lightgrey)
![GUI](https://img.shields.io/badge/GUI-customtkinter-1f6aa5)

![Duplicate File Scanner screenshot](docs/screenshot.png)

## Why this exists

Most duplicate finders compare file *contents*. This one solves a different, very common problem: the same photo, song or document ending up on your disk in several formats.

It knows that **`.jpg` and `.png` are both images**, so `photo_1.jpg` and `photo_1.png` are a match, while **`movie.mp4` and `movie.srt` are not**, because a subtitle file isn't a video.

## Features

- **Format-aware matching.** Extensions are grouped into categories (image, video, audio, document, ...). Only files in the same category can match.
- **Case-insensitive.** `Photo_1.JPG` matches `photo_1.png`.
- **Scan several folders at once.** Compare Downloads against Pictures, or any locations that don't share a parent folder.
- **Same-folder mode.** Optionally only match files that sit side by side.
- **Review before anything is deleted.** Results are shown in groups; you tick exactly the files you want gone.
- **Safe deletion.** Files go to the Recycle Bin / Trash, so mistakes can be undone.
- **Safety warning.** If you select *every* copy in a group, the app asks before continuing.
- **Handles big folders.** Scanning runs in the background (the window never freezes) and results are paginated, with selections kept across pages.

## Quick start

### Linux

```bash
git clone https://github.com/MariosMoraitis/Duplicate_File_Scanner.git
cd Duplicate_File_Scanner

chmod +x install.sh run.sh    # only needed if the files lost their executable bit
./install.sh
./run.sh
```

`install.sh` finds Python 3.10+, installs missing system packages (`python3-tk` and `python3-venv`, via apt, dnf, pacman or zypper), creates a virtual environment in `.venv/` and installs the dependencies. It asks before using `sudo`.

### Windows

Double-click **`install.bat`**, then double-click **`run.bat`**. Or from a terminal:

```bat
git clone https://github.com/MariosMoraitis/Duplicate_File_Scanner.git
cd Duplicate_File_Scanner
install.bat
run.bat
```

`install.bat` looks for Python 3.10+ and, if it isn't there, installs Python 3.12 for you (using `winget`, or a direct download from python.org as a fallback). Then it creates `.venv\` and installs the dependencies. No administrator rights are needed.

> If something goes wrong on Windows, start the app with `run.bat --console` to see error messages.

### Manual install

If you'd rather do it yourself, you need **Python 3.10+ with tkinter**.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python src/app.py
```

On Linux, tkinter comes from your package manager and not from pip:

| Distro family | Command |
|---|---|
| Debian / Ubuntu | `sudo apt install python3-tk python3-venv` |
| Fedora / RHEL | `sudo dnf install python3-tkinter` |
| Arch | `sudo pacman -S tk` |
| openSUSE | `sudo zypper install python3-tk` |

## How to use it

1. Click **Add folder...** and pick a folder. Repeat to add more; **Clear** starts over.
2. *(Optional)* Tick **Only match within the same folder** to ignore matches that are in different folders.
3. Click **Scan**.
4. Browse the groups (use **Prev / Next** if there are many) and tick the files you want to delete.
5. Click **Delete selected** and confirm. The files are moved to the Recycle Bin / Trash.

## How matching works

Every file gets a key made of two things: its **name without the extension, lowercased**, and its **category**. Files that share a key are a group.

| Files | Match? | Why |
|---|---|---|
| `photo_1.jpg` + `photo_1.png` | Yes | both are images |
| `Photo_1.JPG` + `photo_1.png` | Yes | names are compared case-insensitively |
| `report.pdf` + `report.docx` | Yes | both are documents |
| `movie.mp4` + `movie.srt` | No | video vs. an unknown type |
| `song.mp3` + `song.jpg` | No | audio vs. image |
| `cat.jpg` + `dog.png` | No | different names |

Extensions that aren't in any category (like `.srt`) get a category of their own, so they only ever match the exact same extension.

### Customising the categories

The rules live in one place: the `CATEGORIES` dictionary at the top of [`src/scanner.py`](src/scanner.py). Add an extension to a set, or add a whole new category:

```python
CATEGORIES = {
    "image": {".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic"},
    "ebook": {".epub", ".mobi", ".azw3"},     # a new category
    ...
}
```

## Things to know before deleting

- **Matching is by name only.** The app never compares file *contents*. Two unrelated files that happen to share a name (say, `IMG_0001.jpg` from two different cameras) will be flagged. Always check the group before ticking anything.
- **Deletion is reversible.** Files are sent to the Recycle Bin / Trash, not erased.

## Project structure

```
Duplicate_File_Scanner/
├── src/
│   ├── app.py            # the customtkinter GUI
│   ├── scanner.py        # finds and groups files (no GUI code)
│   ├── deleter.py        # moves files to the trash (no GUI code)
│   └── tests/
│       ├── test_scanner.py
│       ├── test_deleter.py
│       └── test_app_gui.py
├── docs/screenshot.png
├── install.sh / install.bat    # one-step setup (Linux / Windows)
├── run.sh / run.bat            # start the app
├── requirements.txt            # runtime dependencies
├── requirements-dev.txt        # + test tools
└── pytest.ini
```

The scanning and deleting logic is kept separate from the GUI on purpose: it can be tested without opening a window.

## Running the tests

```bash
./install.sh --dev          # Windows: install.bat --dev
.venv/bin/python -m pytest -v
```

(On Windows: `.venv\Scripts\python -m pytest -v`.)

The scanner and deleter tests run anywhere. The GUI tests open a real (hidden) window, so they need a display:

- On a normal desktop, nothing special is needed.
- On a headless Linux machine, run `xvfb-run pytest`.
- With no display at all, the GUI tests are **skipped** rather than failing.

## Troubleshooting

**`ModuleNotFoundError: No module named 'tkinter'` (Linux)**
tkinter isn't installed. See the table under [Manual install](#manual-install), or run `./install.sh`, which handles it.

**`python` isn't found after `install.bat` installed it (Windows)**
A freshly installed Python isn't visible to terminals that were already open. Close the window, open a new one and run the script again.

**Only 20 groups are shown at a time**
That's intentional. customtkinter widgets are heavy, and building thousands at once can freeze the app or crash X11 with `BadAlloc`. Use **Prev / Next**. You can change `PAGE_SIZE` in `src/app.py`.

## Roadmap

- [ ] "Select all but the largest" button per group
- [ ] Optional content check (file size / hash) to confirm that matches are real duplicates
- [ ] Image thumbnails for visual comparison
- [ ] Progress bar during scanning

## Built with

- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) for the interface
- [Send2Trash](https://github.com/arsenetar/send2trash) for safe deletion
- [pytest](https://pytest.org) for the tests
