Summary of Changes Made

✅ Fixed the root cause: Added draft dailynote exclusion logic✅
Reverted to key-based detection: More reliable than content
matching✅ Cleaned up code: Removed unused extract_core_content
method

Benefits of the Complete Fix

1. No more duplicates: Draft dailynotes are excluded at source
2. Faster sync: Key-based detection is more efficient than
   content parsing
3. More reliable: Exact Firebase key matching vs fuzzy content
   comparison
4. Cleaner code: Removed workaround logic that's no longer needed

Now you can safely clear and re-sync:

# 1. Test the fix (optional)

docker compose exec eqmd python manage.py sync_firebase_data \
 --credentials-file /path/to/firebase-key.json \
 --database-url <https://your-project.firebaseio.com> \
 --project-name your-project \
 --since-date 2024-01-01 \
 --dry-run --limit 50

# 2. Clear tables and full re-sync

docker compose exec eqmd cp db.sqlite3 db.sqlite3.backup.$(date
+%Y%m%d\_%H%M%S)

docker compose exec eqmd python manage.py shell -c "
from apps.patients.models import Patient
from apps.dailynotes.models import DailyNote
print('Before:', Patient.objects.count(), 'patients,',
DailyNote.objects.count(), 'dailynotes')
Patient.objects.all().delete()
DailyNote.objects.all().delete()
print('After:', Patient.objects.count(), 'patients,',
DailyNote.objects.count(), 'dailynotes')
"

# 3. Full sync from beginning

docker compose exec eqmd python manage.py sync_firebase_data \
 --credentials-file /path/to/firebase-key.json \
 --database-url <https://your-project.firebaseio.com> \
 --project-name your-project \
 --since-date 2020-01-01

The sync will now show:

- Drafts skipped: How many current dailynote drafts were excluded - Regular skipped: Actual duplicates found via Firebase key
- Imported: New unique dailynotes added

For True Database Clearing, You Need Hard Delete

# Option 1: Hard delete (permanent removal)

docker compose exec eqmd python manage.py shell -c "
from apps.patients.models import Patient
from apps.dailynotes.models import DailyNote

# Hard delete - permanently removes from database

Patient.objects.all().hard_delete() # ← Force permanent deletion
DailyNote.objects.all().delete() # ← DailyNote doesn't use
soft delete

print('Tables truly cleared')
"

# Option 2: Include already soft-deleted records

docker compose exec eqmd python manage.py shell -c "
from apps.patients.models import Patient
from apps.dailynotes.models import DailyNote

# Get ALL patients (including previously soft-deleted ones)

Patient.objects.all_with_deleted().hard_delete()
DailyNote.objects.all().delete()

print('All records permanently removed')
"

Why This Matters

- Soft delete: Safer but doesn't free up database space
  completely
- Hard delete: Truly clears tables for fresh sync
- For production re-sync: You probably want hard delete to start completely clean

The choice depends on whether you want to keep a backup of the
old data (soft delete) or completely start fresh (hard delete).
