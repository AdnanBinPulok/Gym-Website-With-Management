# Gym Website With Management

A modern, full-featured gym management web application built with Python. This project provides a complete solution for managing gym memberships, schedules, payments, user accounts, and more, with a clean and extensible codebase.

## Features

- User authentication and account management
- Membership and subscription plans
- Payment processing and history
- Gallery and banners management
- Schedule and class management
- SEO optimization
- Rate limiting and security features
- Email verification and notifications
- Dashboard for users and admins
- RESTful API routes for all major features
- Modular code structure for easy maintenance
- Logging (local and remote server support)

## Project Structure

```
main.py                  # Entry point for the application
requirements.txt         # Python dependencies
services/                # Core services (database, logging, etc.)
modules/                 # Reusable modules (data, mail, storage, etc.)
pages/                   # Page logic for web routes
routes/                  # API and web route handlers
settings/                # Configuration files
static/                  # Static assets (JS, CSS, images)
data/                    # Data files (JSON, images)
secrets/                 # Secret keys and credentials
```

## Data Files

- `data/gallery.json`: List of image URLs for the gym gallery.
- `data/schedule.json`: Weekly gym schedule, with time slots for different genders and open/close status.
- `data/payment_methods.json`: Payment methods (Bkash, Nagad), including icons, numbers, and notes for users.
- `data/config.json`: General gym configuration: name, version, domain, branding images, contact info, social links, currency, admin credentials, timezone, and location.

## Example Hosted Deployment

You can see a live example of this code running at:

**[https://aestheticfitnessgym.com](https://aestheticfitnessgym.com)**

---

## Getting Started

### Prerequisites

- Python 3.12+
- pip

### Installation

1. Clone the repository:
   ```powershell
   git clone https://github.com/adnanbinpulok/Gym_Website_With_Management.git
   cd Gym_Website_With_Management
   ```
2. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

### Running the Application

1. Start the main application:
   ```powershell
   python main.py
   ```
2. Access the website via your local server (default: http://localhost:8000 or as configured).

### Configuration

- Update `settings/config.py` and files in `data/` as needed for your environment.
- Place your secret keys in the `secrets/` directory.
- If you need environment variables, create a `.env` file in the project root.

#### Changing Logo and Favicon

To update the branding images for your gym website:

- Replace `data/images/logo.png` with your own logo file (PNG format recommended).
- Replace `data/images/favicon.png` with your own favicon file (PNG format recommended).

Make sure the filenames remain the same, or update your configuration in `data/config.json` and `settings/config.py` to match your new filenames if you change them.

#### Environment Variables (.env)

You can use a `.env` file in the project root to store sensitive or environment-specific settings. This file is not tracked by git and should be kept private. Example:

```env
# Database configuration
DATABASE_HOST = "example_host"
DATABASE_PORT = "example_port"
DATABASE_USER = "example_user"
DATABASE_PASSWORD = "example_password"
DATABASE_NAME = "example_db"
DATABASE_POOL = 10

API_HOST = "0.0.0.0"
API_PORT = "8000"
BASE_URL = "https://example.com"


SMTP_SERVER = "smtp.example.com"  # Example outgoing mail server
SMTP_PORT = 465  # For SSL
SMTP_USER = "user@example.com"  # Example email
SMTP_PASSWORD = "example_password"  # Example email password


IMAGE_UPLOAD_SERVER_URL = "https://media.example.com"
IMAGE_UPLOAD_SERVER_KEY = "example_upload_key"
```

## Media Server

- I have Media Server build in my repository.
- I will upload that later. Please wait for the next update. of Repo Name: "Media Server"

## Nginx Configuration

A RECORD TO THE SERVER IP IN CLOUDFLARE

```
# ================================
# Trust Cloudflare IPs for real IP logging
# ================================
set_real_ip_from 103.21.244.0/22;
set_real_ip_from 103.22.200.0/22;
set_real_ip_from 103.31.4.0/22;
set_real_ip_from 104.16.0.0/13;
set_real_ip_from 104.24.0.0/14;
set_real_ip_from 108.162.192.0/18;
set_real_ip_from 131.0.72.0/22;
set_real_ip_from 141.101.64.0/18;
set_real_ip_from 162.158.0.0/15;
set_real_ip_from 172.64.0.0/13;
set_real_ip_from 173.245.48.0/20;
set_real_ip_from 188.114.96.0/20;
set_real_ip_from 190.93.240.0/20;
set_real_ip_from 197.234.240.0/22;
set_real_ip_from 198.41.128.0/17;

real_ip_header CF-Connecting-IP;


server {
    listen 80;
    server_name aestheticfitnessgym.com www.aestheticfitnessgym.com;

    location / {
        proxy_pass http://127.0.0.1:8887;
        proxy_http_version 1.1;

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Security headers
        add_header X-Frame-Options "SAMEORIGIN";
        add_header X-Content-Type-Options "nosniff";
        add_header Referrer-Policy "no-referrer-when-downgrade";
        add_header X-XSS-Protection "1; mode=block";
    }
}

server {
    listen 80 default_server;

    server_name _;

    return 403;
}
```

## Logging

- Logs are stored in the `logs/` directory.
- Remote logging is supported and can be configured in the logger.

## Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License.

## Author

- [Adnan Bin Pulok](https://github.com/adnanbinpulok)

---

Feel free to customize this README for your specific deployment, branding, or additional features.
