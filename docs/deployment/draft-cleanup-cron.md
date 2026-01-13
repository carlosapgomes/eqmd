# Draft Cleanup Cron Configuration

Add to crontab:

```bash
# Run every hour to clean up expired drafts
0 * * * * cd /path/to/eqmd && /path/to/uv run python manage.py cleanup_expired_drafts >> /var/log/eqmd/draft-cleanup.log 2>&1
```

Or use systemd timer:

```ini
# /etc/systemd/system/eqmd-draft-cleanup.service
[Unit]
Description=EQMD Draft Cleanup
After=network.target

[Service]
Type=oneshot
User=eqmd
WorkingDirectory=/path/to/eqmd
ExecStart=/path/to/uv run python manage.py cleanup_expired_drafts
```

```ini
# /etc/systemd/system/eqmd-draft-cleanup.timer
[Unit]
Description=Run EQMD Draft Cleanup hourly

[Timer]
OnCalendar=hourly
Persistent=true

[Install]
WantedBy=timers.target
```

## Setup Instructions

### Using Cron

1. Open crontab:
   ```bash
   crontab -e
   ```

2. Add the cron command (adjust paths as needed):
   ```bash
   0 * * * * cd /home/carlos/projects/eqmd && /home/carlos/.local/bin/uv run python manage.py cleanup_expired_drafts >> /var/log/eqmd/draft-cleanup.log 2>&1
   ```

3. Save and exit

### Using Systemd

1. Create the service file:
   ```bash
   sudo nano /etc/systemd/system/eqmd-draft-cleanup.service
   ```

2. Create the timer file:
   ```bash
   sudo nano /etc/systemd/system/eqmd-draft-cleanup.timer
   ```

3. Enable and start the timer:
   ```bash
   sudo systemctl enable eqmd-draft-cleanup.timer
   sudo systemctl start eqmd-draft-cleanup.timer
   ```

4. Check status:
   ```bash
   sudo systemctl status eqmd-draft-cleanup.timer
   ```

## Testing

Test the cleanup command without actually deleting:
```bash
uv run python manage.py cleanup_expired_drafts --dry-run
```