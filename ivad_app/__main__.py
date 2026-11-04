"""WPF developer entry point; legacy Qt lives in history/qt_main.py."""
import argparse
import os
from pathlib import Path
import secrets
import subprocess

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--workspace',type=Path,required=True)
    parser.add_argument('--project',type=Path)
    args=parser.parse_args();repo=Path(__file__).resolve().parent.parent
    workspace=args.workspace.resolve()
    if workspace.is_relative_to(repo):parser.error('Workspace must be outside program directory')
    if args.project and not args.project.resolve().is_relative_to(workspace):parser.error('Project must be inside workspace')
    exe=repo/'wpf_intel/build/final/Ivad.Annotator.Dev.exe'
    if not exe.is_file():parser.error('Build wpf_intel/scripts/build.ps1 -OutputDirectory build/final first')
    workspace.mkdir(parents=True,exist_ok=True)
    env=dict(os.environ,IVAD_NVIDIA_BRIDGE='1',IVAD_IDS_CONTROLLED_ROOT=str(workspace),IVAD_NVIDIA_PYTHON=str(repo/'.venv-media-native-v2/Scripts/python.exe'),IVAD_IPC_TOKEN=secrets.token_hex(32),PYTHONUTF8='1')
    command=[str(exe)]+(['--open-project',str(args.project.resolve())] if args.project else [])
    return subprocess.run(command,cwd=repo,env=env).returncode

if __name__=='__main__':raise SystemExit(main())
