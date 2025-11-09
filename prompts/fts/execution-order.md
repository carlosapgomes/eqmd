# FTS Implementation Execution Order

## 📋 How to Use This Guide

**Follow this exact sequence using the consolidated files:**

1. **📚 Read**: `implementation-plan.md` - Understand the complete plan
2. **💻 Code**: Use `code-examples.md` - Copy exact code for each step
3. **🔍 Reference**: `search-algorithm-details.md` - Technical depth if needed

---

## 🚀 Step-by-Step Execution Sequence

### **Phase 0: User Model Extension** ⏱️ 30 minutes

**Goal**: Add `is_researcher` boolean field to user model

1. **Modify**: `apps/accounts/models.py`

   - Add `is_researcher` field (see code-examples.md #0)

2. **Modify**: `apps/accounts/admin.py`

   - Add field to admin interface (see code-examples.md #0)

3. **Create migration**:

   ```bash
   python manage.py makemigrations accounts
   python manage.py migrate
   ```

4. **Test**: Verify field appears in user admin

---

### **Phase 1: Database Schema** ⏱️ 1-2 hours

**Goal**: Add search vector to DailyNote model

1. **Modify**: `apps/dailynotes/models.py`

   - Add `search_vector` field and GIN index (see code-examples.md #1)

2. **Create migration**:

   ```bash
   python manage.py makemigrations dailynotes
   python manage.py migrate
   ```

3. **Create**: `apps/dailynotes/signals.py`

   - Add signal handler for search vector updates (see code-examples.md #1)

4. **Modify**: `apps/dailynotes/apps.py`

   - Register signals (see code-examples.md #1)

5. **Create**: `apps/dailynotes/management/commands/populate_search_vectors.py`

   - Management command for initial population (see code-examples.md #2)

6. **Run initial population**:

   ```bash
   python manage.py populate_search_vectors --batch-size=1000
   ```

---

### **Phase 2: Research App Creation** ⏱️ 1 hour

**Goal**: Create the research app structure

1. **Create app**:

   ```bash
   python manage.py startapp research apps/research
   ```

2. **Create files** (use code-examples.md #2):

   - `apps/research/apps.py`
   - `apps/research/permissions.py`
   - `apps/research/utils.py`
   - `apps/research/forms.py`
   - `apps/research/views.py`
   - `apps/research/urls.py`

3. **Create template directories**:

   ```bash
   mkdir -p apps/research/templates/research
   ```

---

### **Phase 3: Search Implementation** ⏱️ 2-3 hours

**Goal**: Implement search functionality

1. **Complete**: All files from Phase 2 with the code from code-examples.md #2

2. **Create templates**:

   - `apps/research/templates/research/search.html` (see code-examples.md #6)
   - `apps/research/templates/research/access_denied.html` (see code-examples.md #5)

3. **Test search utilities**:

   ```bash
   python manage.py shell
   >>> from apps.research.utils import get_patient_initials
   >>> get_patient_initials("João da Silva Santos")
   'J.D.S.S.'
   ```

---

### **Phase 4: Frontend Integration** ⏱️ 2 hours

**Goal**: Update navigation and templates

1. **Modify**: `templates/base_app.html`

   - Add new "Pesquisa Clínica" section (see code-examples.md #3)

2. **Test navigation**:
   - Grant researcher access to a test user
   - Verify menu appears only for researchers
   - Test mobile navigation

---

### **Phase 5: URL Configuration** ⏱️ 30 minutes

**Goal**: Wire up URLs

1. **Modify**: `config/settings.py`

   ```python
   INSTALLED_APPS = [
       # ... existing apps ...
       'apps.research',
   ]
   ```

2. **Modify**: `config/urls.py`

   ```python
   # Add to urlpatterns
   path('research/', include('apps.research.urls')),
   ```

3. **Test URL routing**:

   ```bash
   python manage.py check
   python manage.py runserver
   # Visit: http://localhost:8000/research/
   ```

---

### **Phase 6: Testing & Validation** ⏱️ 1-2 hours

**Goal**: Ensure everything works correctly

1. **Grant researcher access**:

   - Go to Django admin
   - Edit a user and check `is_researcher`
   - Verify menu appears

2. **Test search functionality**:

   - Search for medical terms
   - Verify patient initials format (J.D.S.S.)
   - Check age calculation (from matching notes)
   - Test pagination

3. **Performance testing**:

   ```bash
   python manage.py shell
   >>> from apps.research.utils import perform_fulltext_search
   >>> import time
   >>> start = time.time()
   >>> results = perform_fulltext_search("diabetes")
   >>> print(f"Search took: {time.time() - start:.2f}s")
   ```

4. **Database performance**:

   ```sql
   EXPLAIN ANALYZE SELECT * FROM dailynotes_dailynote
   WHERE search_vector @@ to_tsquery('portuguese', 'diabetes');
   ```

---

## ✅ Success Criteria

- [ ] User can be granted researcher access via admin
- [ ] Navigation menu appears only for researchers
- [ ] Search returns patient-centric results
- [ ] Initials include all words (J.D.S.S.)
- [ ] Age calculated from most recent matching note
- [ ] Search is fast (< 500ms for typical queries)
- [ ] Pagination works correctly
- [ ] Access denied page works for non-researchers

---

## 🔧 Troubleshooting

### Common Issues

1. **Search vector not populating**:

   ```bash
   python manage.py populate_search_vectors --dry-run
   ```

2. **Menu not appearing**:

   - Check `user.is_researcher` in shell
   - Clear browser cache
   - Check template syntax

3. **Search returning no results**:

   - Verify GIN index exists
   - Check PostgreSQL version supports full text search
   - Test with simple queries first

4. **Performance issues**:
   - Check GIN index is being used
   - Consider increasing `batch_size` for population
   - Monitor PostgreSQL logs

---

## 📁 File Reference

| Phase | Files Modified/Created                                                                                   |
| ----- | -------------------------------------------------------------------------------------------------------- |
| 0     | `apps/accounts/models.py`, `apps/accounts/admin.py`                                                      |
| 1     | `apps/dailynotes/models.py`, `apps/dailynotes/signals.py`, `apps/dailynotes/apps.py`, management command |
| 2     | `apps/research/` (entire app)                                                                            |
| 3     | Complete research app functionality                                                                      |
| 4     | `templates/base_app.html`                                                                                |
| 5     | `config/settings.py`, `config/urls.py`                                                                   |

**Total Estimated Time: 9.5-13.5 hours**

