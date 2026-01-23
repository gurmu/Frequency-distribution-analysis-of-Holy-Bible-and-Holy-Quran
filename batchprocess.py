docs = list_docs_recursive(SRC_ROOT)
print(f"Found {len(docs)} documents under {SRC_CONTAINER}")

success = 0
skipped = 0
failed = 0

for src in docs:
    rel = src.replace(SRC_ROOT, "", 1)
    pdf_rel = os.path.splitext(rel)[0] + ".pdf"
    dst = DST_ROOT + pdf_rel

    # ensure destination directory exists
    dst_dir = os.path.dirname(dst)
    if dst_dir and not dst_dir.endswith("/"):
        dst_dir += "/"
    dbutils.fs.mkdirs(dst_dir)

    try:
        if SKIP_IF_EXISTS and _exists(dst):
            skipped += 1
            continue

        convert_one(src, dst)
        success += 1

        if success % 25 == 0:
            print(f"Progress: {success}/{len(docs)} (skipped={skipped}, failed={failed})")

    except Exception as e:
        failed += 1
        print(f"FAIL: {src}\n  {e}\n")

print(f"DONE. success={success}, skipped={skipped}, failed={failed}")
print("PDF output root:", DST_ROOT)