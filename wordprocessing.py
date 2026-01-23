def list_office_docs(root: str):
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

docs = list_office_docs(src_root)
print(f"Found {len(docs)} documents in {src_container}")

success, failed = 0, 0

for src in docs:
    rel = src.replace(src_root, "", 1)              # relative path under container
    pdf_rel = os.path.splitext(rel)[0] + ".pdf"     # same path, pdf extension
    dst = dst_root + pdf_rel

    # ensure destination folder exists
    dst_dir = os.path.dirname(dst)
    dbutils.fs.mkdirs(dst_dir)

    try:
        convert_office_to_pdf(src, dst)
        success += 1
        if success % 25 == 0:
            print(f"Progress: {success}/{len(docs)} converted...")
    except Exception as e:
        failed += 1
        print(f"FAIL: {src}\n  {e}\n")

print(f"DONE. Success={success}, Failed={failed}")
print("PDFs written under:", dst_root)