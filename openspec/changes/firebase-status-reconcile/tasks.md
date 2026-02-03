## 1. Discharge Import Reconciliation

- [x] 1.1 Update discharge import command to close active admissions and update patient status via model APIs
- [x] 1.2 Add logging/summary counters for discharge reconciliation actions
- [x] 1.3 Add or update tests covering discharge import status reconciliation

## 2. Firebase Status Sync Reconciliation

- [x] 2.1 Extend Firebase sync to reconcile existing patient status changes (outpatient/deceased) and close active admissions
- [x] 2.2 Create active admission when Firebase status is inpatient/emergency and no active admission exists
- [x] 2.3 Add logging/summary counters for status reconciliation actions
- [x] 2.4 Add or update tests covering Firebase status reconciliation scenarios
