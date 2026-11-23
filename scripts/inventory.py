"""Record installed distributions and collect their unmodified license files."""

from importlib.metadata import distributions
from pathlib import Path
import shutil
import sys


root = Path(sys.argv[1])
installed = []
packages = root / "runtime" / "Lib" / "site-packages"
for distribution in sorted(distributions(path=[str(packages)]), key=lambda item: item.metadata["Name"].lower()):
    name = distribution.metadata["Name"]
    version = distribution.version
    license_name = distribution.metadata.get("License-Expression") or next(
        (entry for entry in distribution.metadata.get_all("Classifier", []) if entry.startswith("License ::")),
        "See upstream distribution")
    urls = distribution.metadata.get_all("Project-URL", [])
    home = distribution.metadata.get("Home-page")
    if home:
        urls.append(home)
    installed.append(f"{name}=={version}\n  {license_name}\n  " + "\n  ".join(urls))
    for entry in distribution.files or ():
        if not any(part.lower().endswith(".dist-info") or part.lower() == "licenses" for part in entry.parts):
            continue
        if not any(word in entry.name.lower() for word in ("license", "licence", "notice", "copying", "copyright")):
            continue
        source = distribution.locate_file(entry)
        if source.is_file():
            target = root / "licenses" / "runtime" / f"{name}-{version}" / entry.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
(root / "RUNTIME-INVENTORY.txt").write_text("\n\n".join(installed) + "\n", encoding="utf-8")
