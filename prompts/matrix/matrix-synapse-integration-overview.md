# Matrix Synapse Integration Plan - Overview

## Project Scope
Add a Matrix Synapse server to EquipeMed for secure messaging, integrated with Django/allauth OIDC authentication, optimized for medical team collaboration and future bot assistance.

## Architecture Summary

### **Domain Structure**
- **Matrix Server**: `matrix.yourhospital.com` (homeserver)
- **Element Client**: `chat.yourhospital.com` (web interface)
- **EquipeMed**: `yourhospital.com` (OIDC provider)

### **Infrastructure Components**
- **Matrix Synapse**: Homeserver with OIDC authentication
- **Element Web**: Customized web client with disabled E2E encryption
- **PostgreSQL**: Shared instance with new `matrix_db` database
- **Nginx**: Reverse proxy for Matrix and Element
- **Docker Network**: Internal communication between services

### **Key Features**
- ✅ **Single non-federated node**
- ✅ **Text messages, audio, PDF, images only**
- ✅ **Disabled E2E encryption by default**
- ✅ **Only DM chats for users, rooms for admin/bots**
- ✅ **Django/allauth OIDC integration**
- ✅ **User lifecycle synchronization**
- ✅ **Bot-friendly environment**

## Resource Allocation (4vCPU/6GB RAM machine)

### **Matrix Synapse Container**
- **Memory**: 512MB limit
- **CPU**: Shared (no limit)
- **Storage**: Docker volume `matrix_media_files` (50GB limit)
- **Database**: `matrix_db` in existing PostgreSQL

### **Element Web Container**
- **Memory**: 128MB limit  
- **CPU**: Shared (no limit)
- **Storage**: Minimal (config files only)

### **Network Configuration**
- **Internal**: Docker network for Matrix ↔ EquipeMed communication
- **External**: Nginx reverse proxy for public access
- **SSL**: Uses existing wildcard certificate setup

## Implementation Phases

### **Phase 1: Infrastructure Setup** (`matrix-synapse-phase1-infrastructure.md`)
- Docker services configuration
- PostgreSQL database setup
- Docker network creation
- Basic nginx configuration

### **Phase 2: Django OIDC Provider** (`matrix-synapse-phase2-django-oidc.md`)
- Install OIDC dependencies
- Configure allauth as identity provider
- Generate RSA keys
- Setup OIDC endpoints

### **Phase 3: Matrix Synapse Configuration** (`matrix-synapse-phase3-synapse-config.md`)
- Homeserver configuration
- OIDC authentication setup
- Security and permission policies
- Room creation restrictions

### **Phase 4: Element Web Client** (`matrix-synapse-phase4-element-web.md`)
- Element deployment and configuration
- Custom config with disabled E2E encryption
- Well-known client configuration
- UI customization for medical use

### **Phase 5: User Management Integration** (`matrix-synapse-phase5-user-management.md`)
- Django app for Matrix integration
- User lifecycle synchronization
- Management commands
- Admin interface integration

### **Phase 6: Testing and Deployment** (`matrix-synapse-phase6-testing-deployment.md`)
- Testing procedures
- Deployment verification
- Troubleshooting guide
- Monitoring setup

## Security Considerations

### **Authentication Flow**
1. User accesses `chat.yourhospital.com`
2. Element redirects to Matrix OIDC endpoint
3. Matrix redirects to EquipeMed OIDC provider
4. User authenticates with EquipeMed credentials
5. Matrix receives user profile and creates/updates Matrix user
6. User logged into Element with Matrix session

### **Access Control**
- **Room Creation**: Admin and bot users only
- **User Registration**: Disabled (OIDC only)
- **Federation**: Completely disabled
- **Guest Access**: Disabled
- **Public Rooms**: Admin control only

### **Data Privacy**
- **E2E Encryption**: Disabled by default for usability
- **Message Retention**: Configurable per room
- **Media Files**: Stored separately from EquipeMed media
- **User Data**: Minimal sync (ID, name, email, role)

## Integration Points

### **EquipeMed → Matrix Sync**
- **User Creation**: Auto-create Matrix user on first login
- **User Updates**: Sync profile changes (name, email)
- **User Deactivation**: Disable Matrix access when EquipeMed user is disabled
- **Admin Status**: Sync superuser status to Matrix admin

### **Future Bot Integration**
- **Bot User**: Dedicated service account with room creation privileges
- **Document Types**: Daily notes, discharge reports, prescriptions
- **Permission Checking**: Bot validates user permissions before actions
- **Template Integration**: Can leverage existing `sample_content` system

## Next Steps

1. **Review all phase documents** in sequential order
2. **Verify SSL configuration** on your deployed machine
3. **Confirm resource allocation** is acceptable
4. **Proceed with Phase 1 implementation** when ready

## Files Created
- `matrix-synapse-phase1-infrastructure.md` - Docker and infrastructure setup
- `matrix-synapse-phase2-django-oidc.md` - Django OIDC provider configuration  
- `matrix-synapse-phase3-synapse-config.md` - Matrix Synapse configuration
- `matrix-synapse-phase4-element-web.md` - Element web client setup
- `matrix-synapse-phase5-user-management.md` - User synchronization system
- `matrix-synapse-phase6-testing-deployment.md` - Testing and deployment procedures