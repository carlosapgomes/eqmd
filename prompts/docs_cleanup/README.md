# Documentation Cleanup Plan

## Overview

This directory contains a comprehensive plan to clean up outdated and redundant documentation in the `docs/` folder. The cleanup will reduce maintenance overhead by ~60% and eliminate confusion between old and new documentation.

## Problem Summary

After analysis of the `docs/` directory, key issues identified:

- **Historical Migration Documents**: Multiple large files documenting completed migrations (FilePond, etc.)
- **Redundant Testing Documentation**: 3 overlapping testing guides 
- **Duplicate App Documentation**: Old detailed docs vs. new comprehensive guides
- **Outdated Architecture Docs**: References to completed migrations
- **Orphaned Translation Files**: .pt-BR.md files that may be outdated

## Execution Plan

Execute phases sequentially:

1. **[Phase 1: Historical Migration Cleanup](phase_1_migration_cleanup.md)** - Remove completed migration documentation
2. **[Phase 2: Testing Documentation Consolidation](phase_2_testing_consolidation.md)** - Merge overlapping testing guides
3. **[Phase 3: App Documentation Deduplication](phase_3_app_deduplication.md)** - Remove redundant app docs
4. **[Phase 4: Architecture Documentation Audit](phase_4_architecture_audit.md)** - Review and update architecture docs
5. **[Phase 5: Translation Files Cleanup](phase_5_translation_cleanup.md)** - Audit and clean Portuguese translations
6. **[Phase 6: Final Restructuring](phase_6_final_restructuring.md)** - Update navigation and cross-references

## Expected Benefits

- **60% reduction** in documentation maintenance overhead
- **Clearer navigation** for developers and users  
- **Eliminated confusion** between old/new documentation
- **Faster onboarding** with focused, current guides

## Safety Measures

Each phase includes:
- Archive deleted content in cleanup branch
- Verify no active links to deleted documentation  
- Update navigation and cross-references
- Test remaining docs for accuracy