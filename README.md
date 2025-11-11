# RouteX

## Overview

**RouteX** is a logistics and shipment management system built with **Django**.  
It simplifies the process of managing warehouses, clients, and shipments by assigning clear roles for **Warehouse Managers** and **Drivers**.  
Each user type has specific permissions, ensuring a secure and efficient workflow from shipment creation to delivery.

---

## User Roles & Permissions

### 🧭 Warehouse Manager

The warehouse manager has full access to administrative operations, including:

- creating **product**
- Creating and managing **shipments**
- Managing **warehouses** and **customers**
- Assigning shipments to drivers
- Monitoring shipment status and delivery progress

### 🚚 Driver

The driver can:

- View all assigned shipments
- Update the shipment status (e.g., ASSIGNED, IN-TRANSIT, DELIVERED)
- Track delivery details and confirm completion

---

## Key Features

- **Role-Based Access Control:** Secure login and permissions for each user type
- **Shipment Management:** Create, assign, and monitor shipment details
- **Driver Dashboard:** Real-time view of assigned deliveries
- **Status Updates:** Drivers can update shipment progress directly
- **Warehouse & custmer Management:** Organized structure for better logistics control

---

## Tech Stack

- **Backend:** Django 5.2.6 + Django REST Framework
- **Database:** PostgreSQL 15+
- **Authentication:** JWT (Simple JWT)
- **API Documentation:** OpenAPI 3.0 (drf-spectacular)
- **Testing:** pytest + pytest-django
- **CI/CD:** GitHub Actions
- **Security:** CORS, HSTS, CSP Headers

## Installation & Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/FatimaaAlzahraa/RouteX.git
   cd RouteX

   ```

2. **Create and activate a virtual environment (Windows)**

   ```bash
   python -m venv venv
   venv\Scripts\activate

   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt

   ```

4. **Environment variables (.env)**

   - Copy the example environment file:

     ```bash
     copy env.example .env
     ```

   - Edit `.env` and configure at minimum:

     ```env
     DJANGO_SECRET_KEY=your-secret-key-here
     DEBUG=True
     DB_NAME=routex
     DB_USER=routex_user
     DB_PASSWORD=your_password
     DB_HOST=127.0.0.1
     DB_PORT=5432
     ```

   - Generate a secure secret key:
     ```bash
     python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
     ```

5. **Run migrations**

   ```bash
   python manage.py makemigrations
   python manage.py migrate

   ```

6. **Create superuser (optional)**

   ```bash
   python manage.py createsuperuser

   ```

7. **Start the development server**
   ```bash
   python manage.py runserver
   ```

---

---

## API Documentation

### Interactive Documentation

- **Swagger UI**: `/api/docs/` - Interactive API explorer with "Try it out" functionality
- **ReDoc**: `/api/redoc/` - Clean, responsive API documentation
- **OpenAPI Schema**: `/api/schema/` - Raw OpenAPI 3.0 schema (JSON)

### API Versioning

All endpoints are versioned under `/api/v1/`. Current version: **v1**

### Authentication

All endpoints require JWT authentication unless stated otherwise.

**1. Login** (`POST /api/v1/auth/login/`)

```json
{
  "phone": "0500000000",
  "password": "your-password"
}
```

Response includes `access`, `refresh` tokens, and user `role`.

**2. Refresh Token** (`POST /api/v1/auth/refresh/`)

```json
{
  "refresh": "your-refresh-token"
}
```

**3. Authentication Header**

Include in all protected requests:

```
Authorization: Bearer <access_token>
```

### Core Endpoints

#### Manager Endpoints

- `GET/POST /api/v1/products/` - Product management
- `GET/POST /api/v1/shipments/` - Shipment management
- `GET /api/v1/manager/shipments/` - List all shipments
- `GET/POST /api/v1/warehouses/` - Warehouse management
- `GET/POST /api/v1/customers/` - Customer management
- `GET /api/v1/drivers/` - Driver status monitoring
- `GET /api/v1/autocomplete/customers/` - Customer search
- `GET /api/v1/autocomplete/shipments/` - Shipment search

#### Driver Endpoints

- `GET /api/v1/driver/shipments/` - View assigned shipments
- `POST /api/v1/status-updates/` - Update shipment status with GPS & photo

#### Profile

- `GET /api/v1/auth/whoami/` - Current user profile and role

---

## Advanced Features

### 🔒 Security

- **CORS** configured for external clients
- **HSTS** with 1-year max-age in production
- **Secure cookies** (HTTPOnly, Secure, SameSite)
- **CSP headers** to prevent XSS
- **Rate limiting** per role (Manager: 10k/hour, Driver: 5k/hour)

### 📄 Pagination

- Default: 10 items per page
- Supports `limit` and `offset` query parameters
- Example: `/api/v1/products/?limit=20&offset=10`

### 🖼️ Image Upload

- Products and status updates support image upload
- Max size: 5MB per image
- Allowed formats: JPG, JPEG, PNG, WebP
- Automatic validation and optimization

### 📊 API Features

- **Filtering & Search**: Use query parameters on list endpoints
- **Ordering**: Sort results with `?ordering=field_name`
- **Autocomplete**: Fast search for customers and shipments
- **Bulk Operations**: Efficient list endpoints with pagination

---

## Testing

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov

# Run specific test file
pytest shipments/test_products.py

# Run tests with specific marker
pytest -m unit
pytest -m api
```

### Test Coverage

Project maintains **>80% code coverage** across all modules.

View HTML coverage report:

```bash
pytest --cov --cov-report=html
# Open htmlcov/index.html in browser
```

---

## CI/CD

### GitHub Actions Workflow

Automated pipeline runs on every push/PR:

1. **Lint & Code Quality**

   - Black (code formatting)
   - isort (import sorting)
   - Flake8 (linting)

2. **Tests & Coverage**

   - Full test suite with PostgreSQL
   - Coverage report uploaded to Codecov
   - Minimum 80% coverage required

3. **Security Scanning**
   - Safety (dependency vulnerabilities)
   - Bandit (security issues)

### SwaggerHub Auto-Publish

On every push to `main`, an additional workflow publishes the OpenAPI schema to SwaggerHub:

- Generates `docs/openapi.json` via `drf-spectacular`
- Uploads to SwaggerHub using `swagger-api/swaggerhub-action`

Set the following repository secrets in GitHub:

- `SWAGGERHUB_API_KEY`: Your SwaggerHub API token
- `SWAGGERHUB_OWNER`: SwaggerHub organization or username (e.g., routex)
- `SWAGGERHUB_API_NAME`: API name in SwaggerHub (e.g., routex-api)
- `SWAGGERHUB_VERSION`: Version label (e.g., 1.0.0)
- `SWAGGERHUB_VISIBILITY`: `PUBLIC` or `PRIVATE`

Manual export locally (Windows PowerShell):

```powershell
.\scripts\export-openapi.ps1 -OutDir docs -BaseName openapi
```

### Local Development

Format code before committing:

```bash
black .
isort .
flake8 .
```

---

## Production Deployment

### Environment Variables

Required in production (`.env`):

```env
DJANGO_SECRET_KEY=<strong-secret-key>
DEBUG=False
DB_NAME=routex_production
DB_USER=routex_prod_user
DB_PASSWORD=<strong-password>
DB_HOST=<database-host>
DB_PORT=5432
SECURE_SSL_REDIRECT=True
SECURE_HSTS_SECONDS=31536000
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

### Security Checklist

- ✅ Strong `SECRET_KEY` (generated randomly)
- ✅ `DEBUG=False`
- ✅ Configure `ALLOWED_HOSTS`
- ✅ Set `CORS_ALLOWED_ORIGINS` explicitly
- ✅ Enable SSL/HTTPS
- ✅ Secure database credentials
- ✅ Regular dependency updates
- ✅ Monitor logs and errors

### Database Migrations

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
```

## Usage

### Login as a Manager:

- Create Product, warehouses, clients, and shipments.

- Assign shipments to drivers.

- Monitor delivery progress.

### Login as a Driver:

- View shipments assigned to you.

- Update shipment statuses as you deliver them.

- Shipment statuses update automatically in the manager’s dashboard.

### Live Demo

Production: https://zahraaayop.pythonanywhere.com/admin
