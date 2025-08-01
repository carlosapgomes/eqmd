# EquipeMed Documentation

**Comprehensive documentation for the EquipeMed medical team collaboration platform**

## 🚀 Quick Start

- **[CLAUDE.md](../CLAUDE.md)** - Essential commands and AI guidance
- **[TESTING.md](TESTING.md)** - Testing strategy and implementation
- **[MIGRATION.md](MIGRATION.md)** - Database migration guide

## 📱 Applications

### Core Medical Apps
- **[Patients](apps/patients.md)** - Patient management, tagging, status tracking
- **[Events](apps/events.md)** - Timeline architecture, event system, 24h edit window
- **[Daily Notes](apps/dailynotes.md)** - Medical evolution notes, duplicate functionality
- **[MediaFiles](apps/mediafiles.md)** - Secure file management, photos/videos, FilePond
- **[PDF Forms](apps/pdf-forms.md)** - Hospital forms with coordinate positioning

### Supporting Apps
- **[Sample Content](sample_content/)** - Template content management
- **[Accounts](../apps/accounts/)** - Custom user model with medical professions

## 🔒 Security & Permissions

- **[Audit History](security/audit-history.md)** - Complete change tracking and monitoring
- **[Permissions](permissions/)** - Role-based access control system

## 🛠️ Development

- **[Template Guidelines](development/template-guidelines.md)** - Django template best practices
- **[Testing Strategy](testing-strategy.md)** - Comprehensive testing approach
- **[Styling](styling.md)** - CSS and frontend guidelines

## 🚀 Deployment

- **[Hospital Configuration](deployment/hospital-configuration.md)** - Environment setup
- **[Sample Data Population](sample-data-population.md)** - Initial data setup

## 📊 Specialized Documentation

### MediaFiles Deep Dive
- **[Database Schema](mediafiles/database_schema.md)** - MediaFiles data model
- **[File Storage Structure](mediafiles/file_storage_structure.md)** - File organization
- **[Security Implementation](mediafiles/security_implementation.md)** - Security measures
- **[Migration Plans](mediafiles/)** - FilePond migration documentation

### Patients App Deep Dive  
- **[API Documentation](patients/api.md)** - Patient API endpoints
- **[Patient Management](patients/patient_management.md)** - Patient workflows
- **[Tags Management](patients/tags_management.md)** - Tagging system

## 📝 Project Information

### Architecture
- **Django 5** medical collaboration platform
- **Single-hospital** patient tracking and care management
- **Bootstrap 5.3** frontend with Portuguese localization
- **UUID identifiers** with comprehensive audit history
- **Role-based permissions** for medical staff

### Key Features
- **Patient Management**: Full CRUD with status tracking
- **Event Timeline**: Medical records with modular card system
- **Secure Media**: Photos/videos with permission-based access
- **Audit Trail**: Complete change history for compliance
- **Hospital Forms**: PDF overlay with drag-and-drop configuration

## 🔧 Development Workflow

1. **Essential Commands**: See [CLAUDE.md](../CLAUDE.md)
2. **Testing**: See [TESTING.md](TESTING.md) 
3. **Database**: See [MIGRATION.md](MIGRATION.md)
4. **Styling**: See [styling.md](styling.md)

## 📚 Additional Resources

- **Legacy Documentation**: Some detailed guides remain in app-specific directories
- **API References**: Check individual app documentation for endpoints
- **Migration Guides**: Historical migration documentation in specialized folders

---

**Note**: This documentation structure was created to separate essential AI guidance ([CLAUDE.md](../CLAUDE.md)) from comprehensive developer documentation. Each section provides both quick reference and detailed implementation guides.