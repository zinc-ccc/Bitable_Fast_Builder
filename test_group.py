from dashboard import load_records, extract_text, FIELD_GROUP
try:
    recs = load_records()
    for r in recs:
        reporter = extract_text(r['fields'].get('汇报人'))
        grp_raw = r['fields'].get(FIELD_GROUP)
        grp_ext = extract_text(grp_raw)
        print(f"[{reporter}] GROUP: '{grp_ext}' (Raw: {grp_raw})")
except Exception as e:
    print(e)
