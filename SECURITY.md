# Security Policy

## Supported versions

This project doesn't have tagged releases yet, so only the **latest code on the `main` branch** is supported. If you found a problem, please check that it still happens on the latest version before reporting it.

## Reporting a vulnerability

Please **don't open a public issue** for security problems. Report them privately instead:

1. Go to the **Security** tab of this repository.
2. Click **Report a vulnerability**.
3. Describe what you found.

A useful report includes:

- what the problem is and why it matters
- steps to reproduce it (a small folder layout that triggers it is ideal)
- your operating system and Python version
- the version or commit of the project you tested

**What to expect:** this is a personal project maintained in spare time, so everything here is best-effort. I aim to acknowledge a report within **7 days**, keep you updated while I investigate, and credit you in the fix if you'd like. How quickly a fix arrives depends on how serious the problem is.

## What counts as a security issue

Because this app deletes files, the most serious problems are the ones that could delete the wrong thing. Examples:

- the app removing a file the user did **not** select, or a file **outside** the folders that were scanned
- symlink or path handling that leads to files outside the chosen folders being affected
- the install scripts (`install.sh`, `install.bat`) being tricked into running unintended code
- a known vulnerability in a dependency (`customtkinter`, `send2trash`) that affects this app

**Not** security issues (please use a normal public issue for these):

- unrelated files being flagged because they share a name. Matching is by name only, as documented in the README, and nothing is deleted without the user ticking the file and confirming.
- a file that can't be deleted because it is locked or you lack permission
- crashes or visual glitches with no impact beyond the app itself

## Security design notes

How the app is built to limit the damage a mistake can do:

- **Nothing is deleted automatically.** Files are only removed after the user ticks them and confirms, and there is an extra warning when *every* copy in a group is selected.
- **Deletion is reversible.** Files are moved to the Recycle Bin / Trash with [Send2Trash](https://github.com/arsenetar/send2trash), not permanently erased.
- **No network access at runtime.** The app only reads the folders you add. It doesn't upload, download or phone home.
- **Symlinked folders aren't followed** while scanning, so a link can't lead the scan outside the folders you picked.
- **The installers are conservative.** `install.sh` only uses `sudo` to install system packages (Python, tkinter, venv), and asks first. `install.bat` installs Python for the current user only, so no administrator rights are needed; if it has to download Python, it does so over HTTPS from python.org or through `winget`. As with any script from the internet, read it before you run it.

## Staying safe when you use it

- **Back up anything important** before a big cleanup, and check the Trash / Recycle Bin before emptying it.
- Read each group before ticking files. Two different files can share a name.
- Keep dependencies up to date: `pip install --upgrade -r requirements.txt` (inside the project's `.venv`).
