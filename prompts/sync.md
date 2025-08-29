After: You can now control what gets synced:

# Step 1: Import ALL patients first (skip dailynotes)

docker compose run --rm \
 -v ./firebase-key.json:/app/firebase-key.json:ro \
 eqmd python manage.py sync_firebase_data \
 --credentials-file firebase-key.json \
 --database-url https://sisphgrs.firebaseio.com/ \
 --project-name sisphgrs \
 --since-date 2016-01-01 \
 --chunk-size 1000 \
 --no-sync-dailynotes

# Step 2: Import ALL dailynotes (skip patients)

docker compose run --rm \
 -v ./firebase-key.json:/app/firebase-key.json:ro \
 eqmd python manage.py sync_firebase_data \
 --credentials-file firebase-key.json \
 --database-url https://sisphgrs.firebaseio.com/ \
 --project-name sisphgrs \
 --since-date 2016-01-01 \
 --chunk-size 500 \
 --no-sync-patients

What happens now:

- Default: Syncs both patients and dailynotes (same as before)
- --no-sync-patients: Only syncs dailynotes
- --no-sync-dailynotes: Only syncs patients
- Both flags: Syncs nothing (useful for testing Firebase connection)

This approach ensures all patients exist before processing any dailynotes, eliminating the "patient_not_found" issue and making the import much more efficient!
