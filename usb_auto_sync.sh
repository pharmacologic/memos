#!/bin/bash

# USB Auto-Sync Service Setup Script
# This script creates all necessary files for automatic USB mounting and syncing

# Configuration - MODIFY THESE VALUES
USB_UUID="YOUR_USB_UUID_HERE"  # Replace with your USB drive's UUID
SOURCE_DIR="/media/usb-sync"   # Mount point for USB drive
DEST_DIR="/home/backup"        # Destination directory for copied files
RSYNC_OPTIONS="-av --delete"   # Rsync options (archive, verbose, delete extra files)

# Create the systemd service file
cat > /etc/systemd/system/usb-sync@.service << EOF
[Unit]
Description=USB Auto Sync Service for %i
After=multi-user.target

[Service]
Type=oneshot
RemainAfterExit=no
ExecStart=/usr/local/bin/usb-sync.sh %i
User=root
Group=root

[Install]
WantedBy=multi-user.target
EOF

# Create the main sync script
cat > /usr/local/bin/usb-sync.sh << 'EOF'
#!/bin/bash

# USB Auto-Sync Script
# Called by systemd service when USB device is detected

# Configuration
USB_UUID="YOUR_USB_UUID_HERE"  # Will be replaced by setup script
SOURCE_DIR="/media/usb-sync"
DEST_DIR="/home/backup"
RSYNC_OPTIONS="-av --delete"
LOG_FILE="/var/log/usb-sync.log"

# Function to log messages
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$LOG_FILE"
}

# Function to send notification (optional)
send_notification() {
    # Uncomment and modify if you want desktop notifications
    # sudo -u username DISPLAY=:0 notify-send "USB Sync" "$1"
    log_message "$1"
}

# Get the device from the parameter
DEVICE="$1"

if [[ -z "$DEVICE" ]]; then
    log_message "ERROR: No device specified"
    exit 1
fi

log_message "Starting sync process for device: $DEVICE"
send_notification "USB drive detected, starting sync..."

# Wait a moment for device to be ready
sleep 2

# Create mount point if it doesn't exist
mkdir -p "$SOURCE_DIR"

# Mount the device
if mount "$DEVICE" "$SOURCE_DIR"; then
    log_message "Successfully mounted $DEVICE to $SOURCE_DIR"
    send_notification "USB drive mounted successfully"
    
    # Create destination directory if it doesn't exist
    mkdir -p "$DEST_DIR"
    
    # Perform the sync
    log_message "Starting rsync: $SOURCE_DIR -> $DEST_DIR"
    if rsync $RSYNC_OPTIONS "$SOURCE_DIR/" "$DEST_DIR/"; then
        log_message "Sync completed successfully"
        send_notification "File sync completed successfully"
    else
        log_message "ERROR: Sync failed"
        send_notification "ERROR: File sync failed"
    fi
    
    # Wait a moment before unmounting
    sleep 2
    
    # Unmount the device
    if umount "$SOURCE_DIR"; then
        log_message "Successfully unmounted $SOURCE_DIR"
        send_notification "USB drive unmounted, process complete"
    else
        log_message "WARNING: Failed to unmount $SOURCE_DIR"
        send_notification "WARNING: Failed to unmount USB drive"
    fi
else
    log_message "ERROR: Failed to mount $DEVICE"
    send_notification "ERROR: Failed to mount USB drive"
    exit 1
fi

log_message "Process completed for device: $DEVICE"
EOF

# Create the udev rule
cat > /etc/udev/rules.d/99-usb-sync.rules << EOF
# USB Auto-Sync Rule
# Triggers when the specific USB drive (by UUID) is connected
ENV{ID_FS_UUID}=="$USB_UUID", ACTION=="add", RUN+="/bin/systemctl start usb-sync@%k.service"
EOF

# Make scripts executable
chmod +x /usr/local/bin/usb-sync.sh

# Replace placeholder UUID in the sync script
sed -i "s/YOUR_USB_UUID_HERE/$USB_UUID/g" /usr/local/bin/usb-sync.sh

# Create log file and set permissions
touch /var/log/usb-sync.log
chmod 644 /var/log/usb-sync.log

# Reload systemd and udev
systemctl daemon-reload
udevadm control --reload-rules

echo "Setup complete!"
echo ""
echo "Configuration:"
echo "  USB UUID: $USB_UUID"
echo "  Mount point: $SOURCE_DIR"
echo "  Destination: $DEST_DIR"
echo "  Log file: /var/log/usb-sync.log"
echo ""
echo "To test, plug in your USB drive and check the log file."
echo "To view logs: tail -f /var/log/usb-sync.log"
echo ""
echo "IMPORTANT: Make sure to modify the configuration variables at the top of this script"
echo "before running it, especially the USB_UUID value!"
EOF