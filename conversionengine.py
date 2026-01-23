import os
import uuid
import shutil
import subprocess
from typing import List

SKIP_IF_EXISTS = True

def _dbfs_local(dbfs_path: str) -> str:
    return "/dbfs/" + dbfs_path.replace("dbfs:/", "", 1)

def _exists(path: str) -> bool:
    try:
        dbutils.fs.ls(path)
        return True
    except Exception:
        return False

def list_docs_recursive(root: str) -> List[str]:
    stack = [root]
    out = []
    while stack:
        p = stack.pop()
        for item in dbutils.fs.ls(p):
            if item.isDir():
                stack.append(item.path)
            else:
                n = item.name.lower()
                if n.endswith(".docx") or n.endswith(".doc"):
                    out.append(item.path)
    return out

def convert_one(src_path: str, dst_path: str) -> None:
    if SKIP_IF_EXISTS and _exists(dst_path):
        return

    work_id = uuid.uuid4().hex
    staging_dir = f"dbfs:/tmp/doc2pdf/{work_id}"
    dbutils.fs.mkdirs(staging_dir)

    ext = os.path.splitext(src_path)[1].lower()
    staged_in = f"{staging_dir}/input{ext}"
    dbutils.fs.cp(src_path, staged_in)

    local_dir = f"/tmp/doc2pdf_{work_id}"
    os.makedirs(local_dir, exist_ok=True)

    local_in = os.path.join(local_dir, f"input{ext}")
    shutil.copyfile(_dbfs_local(staged_in), local_in)

    cmd = [
        "soffice",
        "--headless",
        "--nologo",
        "--nofirststartwizard",
        "--convert-to", "pdf",
        "--outdir", local_dir,
        local_in
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if res.returncode != 0:
        raise RuntimeError(
            f"LibreOffice conversion failed\nSRC: {src_path}\n"
            f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
        )

    # typically input.pdf
    local_pdf = os.path.join(local_dir, "input.pdf")
    if not os.path.exists(local_pdf):
        pdfs = [f for f in os.listdir(local_dir) if f.lower().endswith(".pdf")]
        if not pdfs:
            raise FileNotFoundError(f"No PDF produced for {src_path}")
        local_pdf = os.path.join(local_dir, pdfs[0])

    staged_pdf = f"{staging_dir}/output.pdf"
    shutil.copyfile(local_pdf, _dbfs_local(staged_pdf))

    dbutils.fs.cp(staged_pdf, dst_path)

    # cleanup best-effort
    try:
        shutil.rmtree(local_dir, ignore_errors=True)
        dbutils.fs.rm(staging_dir, recurse=True)
    except Exception:
        pass