"""Build on every save; optionally push only the public JSON data commit."""
import os
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent

def git(*args):
    return subprocess.run(['git',*args],cwd=ROOT,check=True,capture_output=True,text=True,timeout=45,
                          env={**os.environ,'GIT_TERMINAL_PROMPT':'0'})

def refresh_and_publish(source):
    from build_static import build
    build(source=Path(source))
    if os.environ.get('PAGES_AUTO_PUSH')!='1':
        return 'Pin data saved and website rebuilt. Automatic publishing is off; push locations.json to update GitHub Pages.'
    remote=os.environ.get('PAGES_REMOTE','origin');branch=os.environ.get('PAGES_BRANCH','main')
    if remote.startswith('-') or branch.startswith('-'):raise ValueError('Invalid Git target')
    if git('branch','--show-current').stdout.strip()!=branch:raise RuntimeError(f'Check out {branch} before auto-publishing')
    git('check-ref-format','--branch',branch)
    status=git('status','--porcelain','--','locations.json').stdout
    if status:
        git('add','--','locations.json')
        git('commit','--only','-m','Update travel pins','--','locations.json')
    git('push',remote,f'HEAD:refs/heads/{branch}')
    return 'Pin data saved and pushed to GitHub. The Pages deployment is queued; it can take a few minutes.'
