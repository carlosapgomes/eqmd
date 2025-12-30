# Documentation Standards

## Structure Guidelines

### Primary Documentation Hierarchy

1. **`docs/apps/`** - Comprehensive application guides
2. **`docs/security/`** - Security and audit documentation
3. **`docs/development/`** - Development guidelines and best practices
4. **`docs/deployment/`** - Deployment and configuration guides
5. **Technical Reference Directories** - Detailed technical specs

### File Naming Conventions

- **Comprehensive guides**: `docs/apps/{app-name}.md`
- **Technical reference**: `docs/{topic}/{specific-file}.md`
- **Process guides**: `docs/{category}/{process-name}.md`

### Content Guidelines

- **Single source of truth** - Avoid duplicate information
- **Clear hierarchy** - Comprehensive guides vs. technical reference
- **Current information** - Remove outdated migration/historical docs
- **Cross-references** - Link between related documentation

### Maintenance Process

1. **Regular reviews** - Quarterly documentation audits
2. **Update on changes** - Documentation updates with code changes  
3. **Link validation** - Regular broken link checking
4. **User feedback** - Incorporate user experience feedback

### Quality Standards

- **Comprehensive** - Cover all essential use cases
- **Accurate** - Test all procedures and commands
- **Accessible** - Clear navigation and structure
- **Maintainable** - Easy to update and extend

## Navigation Guidelines

### Main Navigation (docs/README.md)

- **Quick Start** - Essential files (CLAUDE.md, TESTING.md, architecture)
- **Applications** - Comprehensive guides vs. technical reference separation
- **Security & Permissions** - Access control and audit documentation
- **Development** - Best practices and guidelines
- **Deployment** - Configuration and setup guides
- **Maintenance** - Ongoing operations and standards

### Cross-Reference Standards

- Use relative paths for internal documentation links
- Provide descriptive link text explaining the purpose
- Update cross-references when moving or renaming files
- Include back-references where appropriate

## Content Quality Checklist

### Before Publishing Documentation

- [ ] All commands and procedures tested
- [ ] Cross-references verified and working
- [ ] Clear navigation structure
- [ ] No duplicate information with other docs
- [ ] Updated date and relevance confirmed

### Documentation Types

#### Comprehensive Guides (`docs/apps/`)

- **Purpose**: Complete implementation documentation
- **Audience**: Developers and power users
- **Content**: Installation, configuration, usage, troubleshooting
- **Maintenance**: Update with every significant feature change

#### Technical Reference (specialized directories)

- **Purpose**: Detailed technical specifications
- **Audience**: Developers working on specific components
- **Content**: Database schemas, API specs, implementation details
- **Maintenance**: Update with structural changes

#### Development Guidelines (`docs/development/`)

- **Purpose**: Code standards and best practices
- **Audience**: All developers
- **Content**: Templates, styling, testing, patterns
- **Maintenance**: Review quarterly, update with new standards

## Maintenance Schedule

### Quarterly Reviews

- Check all documentation for accuracy
- Validate internal links
- Update outdated information
- Review user feedback and usage patterns

### With Code Changes

- Update relevant documentation immediately
- Test all documented procedures
- Update cross-references if structure changes
- Review impact on related documentation

### Annual Audits

- Comprehensive structure review
- Archive or remove obsolete documentation
- Update navigation and organization
- Gather feedback from all user types

## Translation Guidelines

### If Maintaining Translations

- Keep translation files synchronized with English versions
- Use consistent terminology across all languages
- Update translations with content changes
- Mark outdated translations clearly

### Current Status

- Portuguese (.pt-BR) files exist in some directories
- Translation maintenance decisions made during cleanup phases
- Refer to translation audit results for current status
