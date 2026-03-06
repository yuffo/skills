import os
import subprocess
from datetime import datetime

SKILLS_DIR = r"C:\Users\yuff.DESKTOP-55AUCJG\.codebuddy\skills"
GITHUB_REPO = "https://github.com/yuffo/skills.git"

def run_cmd(cmd, cwd=None):
    result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"错误: {result.stderr}")
        return False
    print(result.stdout)
    return True

def backup():
    os.chdir(SKILLS_DIR)
    
    # git add
    if not run_cmd("git add .", cwd=SKILLS_DIR):
        return
    
    # check status
    result = subprocess.run("git status --porcelain", shell=True, cwd=SKILLS_DIR, capture_output=True, text=True)
    if not result.stdout.strip():
        print("没有变更需要提交")
        return
    
    # commit
    date_str = datetime.now().strftime("%Y_%m_%d")
    commit_msg = f"自动备份{date_str}"
    if not run_cmd(f'git commit -m "{commit_msg}"', cwd=SKILLS_DIR):
        return
    
    # push
    if run_cmd("git push origin main", cwd=SKILLS_DIR):
        print(f"备份成功: {commit_msg}")
    else:
        print("推送失败")

if __name__ == "__main__":
    backup()
