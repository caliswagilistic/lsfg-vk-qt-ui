# lsfg-vk-qt-ui
qt user interface for lsfg-vk
## dependencies

- Python 3.7+
- [PySide6](https://pypi.org/project/PySide6/)
- [toml](https://pypi.org/project/toml/)

install dependencies with:

```bash
pip install PySide6 toml
```
run with
```bash
python /script/path/here.py
```
would recommended creating a .desktop file that with an exec of Exec=python /path/to/lsfg-vk-ui.py

example:
```bash
[Desktop Entry]
Name=Lossless Scaling Frame Generation
Comment=Lossless Scaling Frame Generation UI
Exec=python /full/path/to/lsfg-vk-ui.py
Icon=/icon/if/you/want.png

```
