# HospitalUser Model Implementation Plan - Vertical Slicing Approach

## Slice 1: Core Model and Basic Admin Interface

### Step 1: Initial Model Setup

1. Create the HospitalUser model in `apps/hospitals/models.py`:
   - Add UUID primary key
   - Add hospital and user ForeignKeys
   - Add status field with choices
   - Implement `__str__` method
   - Add Meta class with ordering and verbose names

### Step 2: Basic Admin Integration

1. Register HospitalUser model in `apps/hospitals/admin.py`
2. Configure basic list_display and search_fields

### Step 3: Create and Apply Migrations

1. Run `python manage.py makemigrations`
2. Run `python manage.py migrate`

### Step 4: Test Basic Functionality

1. Create test for model creation and string representation
2. Verify admin interface access

## Slice 2: Tracking Fields and User Association

### Step 1: Add Tracking Fields

1. Add created_at, updated_at, created_by, updated_by fields
2. Update migrations

### Step 2: Implement Save Method Override

1. Override save method to handle user tracking

### Step 3: Test Tracking Functionality

1. Create tests for tracking fields
2. Test automatic timestamp updates

## Slice 3: URL Configuration and get_absolute_url

### Step 1: Implement get_absolute_url Method

1. Add the method to return detail view URL

### Step 2: Update URL Configuration

1. Add URL patterns for hospital user views in `apps/hospitals/urls.py`

### Step 3: Test URL Resolution

1. Create tests for URL resolution
2. Test get_absolute_url method

## Slice 4: List View Implementation

### Step 1: Create List View

1. Implement HospitalUserListView in `apps/hospitals/views.py`
2. Create list template in `templates/hospitals/hospital_user_list.html`

### Step 2: Add Filtering by Hospital

1. Configure filtering by hospital in the list view

### Step 3: Test List View

1. Create tests for list view
2. Test hospital filtering functionality

## Slice 5: Detail View Implementation

### Step 1: Create Detail View

1. Implement HospitalUserDetailView in views.py
2. Create detail template in `templates/hospitals/hospital_user_detail.html`

### Step 2: Test Detail View

1. Create tests for detail view

## Slice 6: Create and Update Views

### Step 1: Create Basic ModelForm

1. Create `apps/hospitals/forms.py` if not exists
2. Implement HospitalUserForm with appropriate fields and validation

### Step 2: Implement Create View

1. Create HospitalUserCreateView in views.py
2. Create form template in `templates/hospitals/hospital_user_form.html`
3. Add permission requirements

### Step 3: Implement Update View

1. Create HospitalUserUpdateView in views.py
2. Reuse the form template
3. Add permission requirements

### Step 4: Test Create and Update Views

1. Create tests for create functionality
2. Test update functionality
3. Test permission enforcement

## Slice 7: Delete/Deactivate Functionality

### Step 1: Implement Status Toggle View

1. Create HospitalUserToggleStatusView in views.py
2. Create confirmation template
3. Add permission requirements

### Step 2: Test Status Toggle Functionality

1. Create tests for status toggle view
2. Test permission enforcement

## Slice 8: User Hospital Assignment

### Step 1: Create Hospital Assignment Form

1. Implement a form for assigning users to hospitals
2. Add validation to prevent duplicate assignments

### Step 2: Create Assignment View

1. Implement view for hospital assignment
2. Create template for assignment interface

### Step 3: Test Assignment Functionality

1. Create tests for assignment process
2. Test validation rules

## Slice 9: User Hospital Dashboard

### Step 1: Create User Hospital Dashboard View

1. Implement view showing hospitals a user belongs to
2. Create dashboard template

### Step 2: Add Quick Actions

1. Add actions for managing hospital memberships
2. Include status toggle buttons

### Step 3: Test Dashboard Functionality

1. Create tests for dashboard view
2. Test action buttons

## Slice 10: Hospital Staff Management

### Step 1: Create Hospital Staff View

1. Implement view showing all users in a hospital
2. Create staff management template

### Step 2: Add Staff Filtering

1. Add filters by status, role, etc.
2. Implement search functionality

### Step 3: Add Bulk Actions

1. Implement bulk status changes
2. Add bulk role assignments (if applicable)

### Step 4: Test Staff Management

1. Create tests for staff view
2. Test filtering and search
3. Test bulk actions
