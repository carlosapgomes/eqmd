#!/bin/bash
# create_eqmd_user.sh
# 
# EquipeMed User Creation Script
# Handles UID conflicts and creates eqmd system user for Docker deployment

set -e

REQUESTED_UID=${1:-1001}
REQUESTED_GID=${2:-1001}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

# Function to find available UID
find_available_uid() {
    local start_uid=$1
    for ((uid=start_uid; uid<start_uid+100; uid++)); do
        if ! getent passwd $uid >/dev/null; then
            echo $uid
            return
        fi
    done
    print_error "No available UID found in range $start_uid-$((start_uid+99))"
    exit 1
}

# Function to find available GID
find_available_gid() {
    local start_gid=$1
    for ((gid=start_gid; gid<start_gid+100; gid++)); do
        if ! getent group $gid >/dev/null; then
            echo $gid
            return
        fi
    done
    print_error "No available GID found in range $start_gid-$((start_gid+99))"
    exit 1
}

# Function to show help
show_help() {
    cat << EOF
EquipeMed User Creation Script

Usage: $0 [UID] [GID]

Arguments:
  UID     User ID (default: 1001)
  GID     Group ID (default: 1001)

Examples:
  $0                    # Use default UID 1001
  $0 1002              # Use UID 1002, GID 1002
  $0 1002 1003         # Use UID 1002, GID 1003
  $0 5001              # Use high UID to avoid conflicts

This script:
- Creates eqmd system user if it doesn't exist
- Handles UID conflicts by finding alternative UIDs
- Exports EQMD_UID and EQMD_GID environment variables
- Sets up proper user for Docker deployment

The created user:
- Has no login shell (/usr/sbin/nologin)
- Has no home directory (/nonexistent)
- Is a system user (--system flag)
- Used only for running Docker containers
EOF
}

# Check for help flag
if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    show_help
    exit 0
fi

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   print_error "This script must be run as root"
   print_info "Usage: sudo $0 [UID] [GID]"
   exit 1
fi

print_info "EquipeMed User Creation Script"
print_info "Requested UID: $REQUESTED_UID, GID: $REQUESTED_GID"

# Check if eqmd user already exists
if getent passwd eqmd >/dev/null; then
    EXISTING_UID=$(id -u eqmd)
    EXISTING_GID=$(id -g eqmd)
    print_status "eqmd user already exists with UID:$EXISTING_UID GID:$EXISTING_GID"
    
    # Export for Docker usage
    export EQMD_UID=$EXISTING_UID
    export EQMD_GID=$EXISTING_GID
    
    # Also write to environment file for persistence
    cat > /tmp/eqmd_user_env << EOF
export EQMD_UID=$EXISTING_UID
export EQMD_GID=$EXISTING_GID
EOF
    
    print_info "Environment variables exported and saved to /tmp/eqmd_user_env"
    print_info "Source this file in your scripts: source /tmp/eqmd_user_env"
    exit 0
fi

# Check if requested UID is available
if getent passwd $REQUESTED_UID >/dev/null; then
    CONFLICTING_USER=$(getent passwd $REQUESTED_UID | cut -d: -f1)
    print_warning "UID $REQUESTED_UID is already used by: $CONFLICTING_USER"
    
    # Show what the conflicting user is used for
    USER_PROCESSES=$(ps -u $CONFLICTING_USER --no-headers 2>/dev/null | wc -l || echo "0")
    if [ "$USER_PROCESSES" -gt 0 ]; then
        print_warning "User $CONFLICTING_USER has $USER_PROCESSES active processes"
        print_warning "Consider using a different UID or stopping processes first"
    fi
    
    # Find alternative
    AVAILABLE_UID=$(find_available_uid $REQUESTED_UID)
    print_info "Using alternative UID: $AVAILABLE_UID"
    REQUESTED_UID=$AVAILABLE_UID
    REQUESTED_GID=$AVAILABLE_UID
fi

# Check if requested GID is available
if getent group $REQUESTED_GID >/dev/null 2>&1; then
    CONFLICTING_GROUP=$(getent group $REQUESTED_GID | cut -d: -f1)
    if [ "$CONFLICTING_GROUP" != "eqmd" ]; then
        print_warning "GID $REQUESTED_GID is already used by group: $CONFLICTING_GROUP"
        
        # Find alternative GID
        AVAILABLE_GID=$(find_available_gid $REQUESTED_GID)
        print_info "Using alternative GID: $AVAILABLE_GID"
        REQUESTED_GID=$AVAILABLE_GID
    fi
fi

print_info "Creating eqmd user with UID:$REQUESTED_UID GID:$REQUESTED_GID"

# Create group first
if ! getent group eqmd >/dev/null; then
    if groupadd -r -g $REQUESTED_GID eqmd; then
        print_status "Created eqmd group with GID $REQUESTED_GID"
    else
        print_error "Failed to create eqmd group"
        exit 1
    fi
fi

# Create user
if useradd -r -u $REQUESTED_UID -g eqmd -s /usr/sbin/nologin -d /nonexistent eqmd; then
    print_status "Created eqmd user with UID $REQUESTED_UID"
else
    print_error "Failed to create eqmd user"
    exit 1
fi

# Verify user creation
CREATED_UID=$(id -u eqmd)
CREATED_GID=$(id -g eqmd)

if [ "$CREATED_UID" -eq "$REQUESTED_UID" ] && [ "$CREATED_GID" -eq "$REQUESTED_GID" ]; then
    print_status "User verification successful"
else
    print_error "User verification failed. Expected UID:$REQUESTED_UID GID:$REQUESTED_GID, got UID:$CREATED_UID GID:$CREATED_GID"
    exit 1
fi

# Export environment variables
export EQMD_UID=$REQUESTED_UID
export EQMD_GID=$REQUESTED_GID

# Save environment variables for persistence
cat > /tmp/eqmd_user_env << EOF
export EQMD_UID=$REQUESTED_UID
export EQMD_GID=$REQUESTED_GID
EOF

print_status "Environment variables exported and saved to /tmp/eqmd_user_env"
print_info "To use in other scripts, run: source /tmp/eqmd_user_env"

echo ""
print_status "eqmd user creation completed successfully!"
print_info "User details:"
echo "  Username: eqmd"
echo "  UID: $REQUESTED_UID"
echo "  GID: $REQUESTED_GID"
echo "  Shell: /usr/sbin/nologin"
echo "  Home: /nonexistent"
echo ""
print_info "Next steps:"
echo "1. Source the environment file: source /tmp/eqmd_user_env"
echo "2. Build Docker image with: docker build --build-arg USER_ID=\$EQMD_UID --build-arg GROUP_ID=\$EQMD_GID ."
echo "3. Or run installation script that will use these variables automatically"