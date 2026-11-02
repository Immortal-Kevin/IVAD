"""Isolated native-media service environment; copies only resolved runtime deps.

Not a distribution build. Image operations use Pillow; neither NumPy,
PySide6 nor PyAV is included here. The old candidate remains untouched.
"""
from importlib.metadata import distributions
import json
from pathlib import Path
import re
import shutil
import venv
from packaging.requirements import Requirement

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'.venv-p1/Lib/site-packages'
TARGET=ROOT/'.venv-media-native-v2'

def key(name):return re.sub('[-_.]+','-',name).lower()

if __name__=='__main__':
    if TARGET.exists():raise RuntimeError('Refusing to overwrite environment')
    installed={key(d.metadata['Name']):d for d in distributions(path=[str(SOURCE)])}
    wanted={'sqlalchemy','alembic','pillow','pyyaml'}
    pending=list(wanted)
    while pending:
        dist=installed[pending.pop()]
        for raw in dist.requires or []:
            dependency=Requirement(raw)
            if dependency.marker and not dependency.marker.evaluate({'extra':''}):continue
            name=key(dependency.name)
            if name not in wanted:wanted.add(name);pending.append(name)
    assert not wanted.intersection({'av','pyside6','shiboken6','ultralytics','opencv-python','numpy'})
    venv.EnvBuilder(with_pip=False).create(TARGET)
    for name in sorted(wanted):
        for item in installed[name].files or []:
            source=Path(installed[name].locate_file(item)).resolve()
            if not source.is_relative_to(SOURCE.resolve()) or '__pycache__' in source.parts:continue
            if source.is_file():
                destination=TARGET/'Lib/site-packages'/source.relative_to(SOURCE.resolve())
                destination.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(source,destination)
    result={name:installed[name].version for name in sorted(wanted)}
    (ROOT/'artifacts/permissive-20261102/media-environment-v2.json').write_text(json.dumps(dict(packages=result,distribution='BLOCKED',reason='Whole product WPF/IDS/RF license gates remain open'),indent=2),encoding='utf8')
    print(json.dumps(result))
