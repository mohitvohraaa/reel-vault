#!/usr/bin/env bash
# End-to-end smoke test against the running Docker stack (http://localhost:8000).
set -e
API=http://localhost:8000/api
ZIP=sample_data/instagram_export.zip

echo "== 1. Upload export =="
UP=$(curl -s -F "file=@${ZIP};type=application/zip" ${API}/ingestion/upload)
echo "$UP" | python -m json.tool | head -30
JOB=$(echo "$UP" | python -c "import sys,json;print(json.load(sys.stdin)['job_id'])")
echo "job_id=$JOB"

echo "== 2. Import alt-account conversation =="
curl -s -X POST ${API}/ingestion/import -H "Content-Type: application/json" \
  -d "{\"job_id\": ${JOB}, \"thread_id\": \"my_alt_account_17b2f9\"}" \
  | python -c "import sys,json;d=json.load(sys.stdin);print('status',d['status']);print('report',json.dumps(d['report'],indent=2))"

echo "== 3. Reels + stats =="
curl -s "${API}/reels?page_size=50" | python -c "import sys,json;d=json.load(sys.stdin);print('total reels',d['total']);[print(' -',r['normalized_url'],r['processing_status']) for r in d['items']]"
curl -s ${API}/reels/stats | python -m json.tool

echo "== Done. (Synthetic reels are expected to be media_unavailable/insufficient_content.) =="
