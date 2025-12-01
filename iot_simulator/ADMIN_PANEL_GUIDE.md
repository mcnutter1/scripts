# Admin Panel Guide - HP Printer Simulator

## Overview

The HP Printer Simulator now includes a **secure admin panel** that allows administrators to view, download, and analyze all print jobs received by the simulator.

## Features

### 🔐 Secure Authentication
- Password-protected admin access
- Session-based authentication
- Secure password hashing (SHA-256)
- Session cookies with HttpOnly flag

### 📊 Print Job Dashboard
- View all received print jobs in a table
- Sort by job ID, timestamp, source IP
- Real-time statistics:
  - Total print jobs
  - Total pages printed
  - Total data size
- Auto-refresh every 30 seconds

### 📥 Download Print Jobs
- Download any print job file
- Original file format preserved (PDF, PostScript, PCL)
- Proper MIME types for browser handling

### 👁️ View Print Job Details
- View file information and metadata
- Hex dump preview of binary files
- Text preview for readable formats
- File size and type information

## Default Credentials

**⚠️ IMPORTANT: Change these in production!**

- **Username**: `admin`
- **Password**: `admin123`

### Changing the Admin Password

Edit `/Users/robmcnutt/Documents/forescout-scripts-code/scripts/iot_simulator/servers/printer_web_server.py`:

```python
# Find this section near the top of the file:
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = hashlib.sha256("admin123".encode()).hexdigest()

# Generate a new password hash:
# python3 -c "import hashlib; print(hashlib.sha256('YourNewPassword'.encode()).hexdigest())"

# Replace with your new hash:
ADMIN_PASSWORD_HASH = "your_new_hash_here"
```

Or change the username:
```python
ADMIN_USERNAME = "youradmin"
```

## Accessing the Admin Panel

### Method 1: Navigation Link
1. Open the printer web interface: `http://192.168.1.100/`
2. Click the **🔐 Admin** link in the top-right of the navigation bar
3. Enter credentials
4. Access the admin dashboard

### Method 2: Direct URL
1. Navigate to: `http://192.168.1.100/admin`
2. You'll be redirected to the login page if not authenticated
3. Enter credentials
4. Access the admin dashboard

## Using the Admin Panel

### Login Page
```
URL: http://192.168.1.100/admin/login
```

Features:
- Username and password fields
- Error messages for failed login attempts
- Link back to printer home page
- Secure form submission (POST)

### Admin Dashboard
```
URL: http://192.168.1.100/admin
```

Features:
- **Statistics Cards**: Quick overview of print job metrics
- **Print Job Table**: Detailed list of all print jobs
- **Refresh Button**: Manual refresh
- **Auto-refresh**: Automatic refresh every 30 seconds
- **Logout Button**: End session and return to home

#### Print Job Table Columns
| Column | Description |
|--------|-------------|
| Job ID | Unique identifier for the print job |
| Timestamp | When the job was received (YYYY-MM-DD HH:MM:SS) |
| Source IP | IP address of the client that sent the job |
| Type | Document type (PDF, PostScript, PCL, Unknown) |
| Pages | Estimated number of pages |
| Size | File size in KB |
| Status | Job status (completed, pending, failed) |
| Actions | Download and View buttons |

### Viewing a Print Job
```
URL: http://192.168.1.100/admin/view?file=<filename>
```

Features:
- File information (name, type, size)
- Hex dump preview (first 1000 bytes)
- Text preview (for readable formats)
- Download button
- Back to admin panel link

### Downloading a Print Job
```
URL: http://192.168.1.100/admin/download?file=<filename>
```

- Downloads the original print job file
- Proper filename and content-type headers
- Works for PDF, PostScript, PCL, and other formats

### Logout
```
URL: http://192.168.1.100/admin/logout
```

- Ends the session
- Clears session cookie
- Redirects to printer home page

## Security Features

### Session Management
- Session tokens generated with `secrets.token_urlsafe(32)`
- 256-bit random session tokens
- Sessions stored in memory
- Automatic expiration on server restart

### Password Security
- Passwords hashed with SHA-256
- No plaintext passwords stored
- Constant-time comparison (via hash matching)

### HTTP Security Headers
- `HttpOnly` flag on session cookies (prevents JavaScript access)
- `Server` header spoofed as `HP-ChaiSOE/2.0`
- Proper `Content-Disposition` headers for downloads

### Access Control
- All admin routes require authentication
- Unauthenticated requests redirected to login
- Session validation on every admin request
- Logout clears session immediately

## Admin Panel Screenshots (Text View)

### Login Page
```
┌─────────────────────────────────────┐
│     🔐 Admin Panel                  │
│     HP LaserJet Enterprise M609dn   │
│                                     │
│     Username: [____________]        │
│     Password: [____________]        │
│                                     │
│          [ Login ]                  │
│                                     │
│     ← Back to Printer Home          │
└─────────────────────────────────────┘
```

### Dashboard
```
┌──────────────────────────────────────────────────────┐
│ 🔐 Admin Panel - Print Jobs          [ Logout ]      │
├──────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │    25    │  │   375    │  │  12.5 MB │          │
│  │Total Jobs│  │Total Pages│  │Total Size│          │
│  └──────────┘  └──────────┘  └──────────┘          │
│                                                      │
│  [ 🔄 Refresh ]                                      │
│                                                      │
│  Print Job History                                   │
│  ┌───────────────────────────────────────────────┐  │
│  │ ID│Timestamp      │Source    │Type│Pages│...  │  │
│  ├───┼───────────────┼──────────┼────┼─────┼───  │  │
│  │ 1 │2023-12-01 ... │192.168...│PDF │ 3   │...  │  │
│  │ 2 │2023-12-01 ... │192.168...│PS  │ 5   │...  │  │
│  └───────────────────────────────────────────────┘  │
│                                                      │
└──────────────────────────────────────────────────────┘
```

## Technical Implementation

### Session Storage
```python
active_sessions = {
    "token_string": {
        "username": "admin",
        "created": "2023-12-01T14:30:22.123456",
        "ip": "192.168.1.50"
    }
}
```

### Authentication Flow
```
1. User submits login form (POST /admin/login)
2. Server validates credentials (username + password hash)
3. Server generates session token (secrets.token_urlsafe(32))
4. Server stores session in active_sessions dict
5. Server sends session cookie to browser
6. Browser includes cookie in subsequent requests
7. Server validates cookie on each admin page request
8. User clicks logout → session deleted, cookie cleared
```

### Print Job Data Flow
```
Print Job Received → Saved to print_jobs/
                   → Logged to print_log.json
                   → Available in admin panel
                   → Can be viewed/downloaded
```

## Monitoring and Logging

All admin panel activity is logged:

```bash
# View admin access logs
tail -f logs/printer_web_server.log | grep admin

# View login attempts
grep "Admin login" logs/printer_web_server.log

# View failed login attempts
grep "Failed admin login" logs/printer_web_server.log
```

## Troubleshooting

### Can't Access Admin Panel

**Problem**: Page not loading
- **Solution**: Ensure web server is running on port 80
- **Check**: `sudo netstat -tulpn | grep :80`

### Login Not Working

**Problem**: "Invalid username or password"
- **Solution**: Verify credentials (default: admin / admin123)
- **Check**: Ensure password hash is correct in source code
- **Note**: Password is case-sensitive

### Session Expires Immediately

**Problem**: Redirected to login after successful login
- **Solution**: Check browser cookie settings
- **Check**: Ensure cookies are enabled
- **Note**: Session cookies are required

### Print Jobs Not Showing

**Problem**: Dashboard shows no jobs
- **Solution**: Check print_jobs directory exists
- **Check**: `ls -la print_jobs/`
- **Check**: Verify print_log.json exists and is valid JSON
- **Test**: Send a test print job first

### Can't Download Files

**Problem**: Download link doesn't work
- **Solution**: Check file permissions on print_jobs directory
- **Check**: `ls -la print_jobs/<filename>`
- **Check**: Verify file exists

## API Endpoints

For programmatic access (requires authentication):

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/admin` | Admin dashboard | Yes |
| GET | `/admin/login` | Login page | No |
| POST | `/admin/login` | Login form submission | No |
| GET | `/admin/logout` | Logout | Yes |
| GET | `/admin/view?file=X` | View print job details | Yes |
| GET | `/admin/download?file=X` | Download print job | Yes |

## Best Practices

### Security
1. **Change default password** immediately
2. **Use HTTPS** in production (requires reverse proxy)
3. **Limit access** to admin panel by IP if possible
4. **Monitor logs** for unauthorized access attempts
5. **Regular session cleanup** (implement if long-running)

### Operations
1. **Regular backups** of print_jobs directory
2. **Disk space monitoring** (print jobs accumulate)
3. **Log rotation** for printer_web_server.log
4. **Periodic cleanup** of old print jobs

### Maintenance
1. **Review print logs** regularly
2. **Archive old jobs** to free space
3. **Update password** periodically
4. **Monitor failed login attempts**

## Future Enhancements

Possible future features:
- Multiple admin users
- Role-based access control
- Print job deletion from UI
- Print job preview rendering (convert to images)
- Search and filter capabilities
- Export print log as CSV
- Email notifications for new print jobs
- Print job analytics and charts
- Session timeout configuration
- Password change UI
- LDAP/Active Directory integration

## Example Usage

### 1. View Recent Print Jobs
```bash
# Access admin panel
# URL: http://192.168.1.100/admin
# Login: admin / admin123
# View table of all jobs
```

### 2. Download a Print Job
```bash
# Click "Download" button next to desired job
# Or use direct URL:
curl -H "Cookie: session=YOUR_SESSION_TOKEN" \
  http://192.168.1.100/admin/download?file=job_1_20231201_143022.pdf \
  -o downloaded_job.pdf
```

### 3. Automated Monitoring
```python
import requests
import json

# Login
session = requests.Session()
login_data = {'username': 'admin', 'password': 'admin123'}
session.post('http://192.168.1.100/admin/login', data=login_data)

# Get admin dashboard (parse HTML or use print_log.json directly)
with open('print_jobs/print_log.json') as f:
    jobs = json.load(f)
    
print(f"Total jobs: {len(jobs)}")
for job in jobs[-5:]:  # Last 5 jobs
    print(f"Job {job['job_id']}: {job['pages']} pages from {job['source_ip']}")
```

---

## Quick Reference

**Default Login**: admin / admin123  
**Admin URL**: http://192.168.1.100/admin  
**Print Jobs Dir**: `iot_simulator/print_jobs/`  
**Print Log**: `iot_simulator/print_jobs/print_log.json`  
**Web Server Log**: `iot_simulator/logs/printer_web_server.log`  

**Change Password**: Edit `ADMIN_PASSWORD_HASH` in `servers/printer_web_server.py`  
**Session Duration**: Until server restart or manual logout  
**Auto-refresh**: Every 30 seconds on admin dashboard  

---

**🔐 Keep your admin credentials secure!**
