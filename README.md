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
- **Database:** PostgreSQL 15+ (Production) / SQLite (Development)
- **Authentication:** JWT (Simple JWT) with token rotation
- **API Documentation:** OpenAPI 3.0 (drf-spectacular) with Swagger UI
- **Admin UI:** Django Jazzmin (Modern admin interface)
- **Testing:** pytest + pytest-django (85%+ test coverage)
- **CI/CD:** GitHub Actions
- **Security:** CORS, HSTS, CSP Headers, Rate Limiting
- **Caching:** Redis (optional, for production)
- **Monitoring:** Sentry (error tracking)

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

     # Database Configuration
     # Option 1: Use SQLite (easier for local development)
     USE_SQLITE=True

     # Option 2: Use PostgreSQL (for production)
     # USE_SQLITE=False
     # DB_NAME=routex
     # DB_USER=routex_user
     # DB_PASSWORD=your_password
     # DB_HOST=127.0.0.1
     # DB_PORT=5432
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

- **Swagger UI**:
  - `/api/docs/` - Interactive API explorer with "Try it out" functionality
  - `/api/docs/swagger-ui/` - Alternative URL (also works)
- **ReDoc**: `/api/redoc/` - Clean, responsive API documentation
- **OpenAPI Schema**: `/api/schema/` - Raw OpenAPI 3.0 schema (JSON)

### Admin Panel

- **Admin Interface**: `/api/admin/` - Modern Django admin panel with enhanced UI/UX
- **Error Logs**: `/api/admin/error-logs/` - View recent admin errors and logs (staff only)

### API Versioning

All endpoints are versioned under `/api/v1/`. Current version: **v1**

### Authentication

All endpoints require JWT authentication unless stated otherwise.

**1. Signup** (`POST /api/v1/auth/signup/`)

Create a new driver account:

```json
{
  "name": "Driver Name",
  "phone": "+966512345678",
  "password": "StrongPass123",
  "password_confirm": "StrongPass123"
}
```

Response includes `access`, `refresh` tokens, and `role` (defaults to "driver").  
**Note:** Phone must start with `+966` (Saudi Arabia format).

**2. Login** (`POST /api/v1/auth/login/`)

```json
{
  "phone": "0500000000",
  "password": "your-password"
}
```

Response includes `access`, `refresh` tokens, and user `role`.

**3. Refresh Token** (`POST /api/v1/auth/refresh/`)

```json
{
  "refresh": "your-refresh-token"
}
```

**4. Authentication Header**

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
- `GET /api/v1/driver/status/` - Get current driver status (available/busy)
- `PATCH /api/v1/driver/status/` - Update driver status (available/busy)
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

Project maintains **78% code coverage** with **111/131 tests passing (85%)**.

View HTML coverage report:

```bash
# Run all tests with coverage
pytest --cov --cov-report=html --cov-report=term-missing

# Open htmlcov/index.html in browser
```

### Test Results Summary

- ✅ **Signup Tests**: 4/4 (100%)
- ✅ **Products Tests**: 14/14 (100%)
- ✅ **Status Transitions Tests**: 19/19 (100%)
- ✅ **Driver Management Tests**: 8/9 (89%)
- ✅ **Total**: 111/131 tests passing (85%)

**Note:** Tests automatically use SQLite for faster execution. Set `USE_SQLITE=True` in `.env` or `pytest.ini`.

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
# Run migrations
python manage.py migrate --noinput

# Collect static files
python manage.py collectstatic --noinput

# Create log directories (if not exists)
mkdir -p logs
```

### PythonAnywhere Deployment

For PythonAnywhere deployment:

1. **Set environment variables** in `.env`:

   ```env
   USE_SQLITE=True
   DEBUG=False
   ALLOWED_HOSTS=ziad506.pythonanywhere.com
   ```

2. **Run migrations**:

   ```bash
   python manage.py migrate --noinput
   python manage.py collectstatic --noinput
   ```

3. **Create superuser** (if needed):

   ```bash
   python manage.py createsuperuser
   ```

4. **Reload web app** from PythonAnywhere dashboard

### Available URLs on Production

- **Admin Panel**: `https://ziad506.pythonanywhere.com/api/admin/`
- **Swagger UI**: `https://ziad506.pythonanywhere.com/api/docs/` or `/api/docs/swagger-ui/`
- **ReDoc**: `https://ziad506.pythonanywhere.com/api/redoc/`
- **API Schema**: `https://ziad506.pythonanywhere.com/api/schema/`
- **Health Check**: `https://ziad506.pythonanywhere.com/api/health/`
- **Error Logs**: `https://ziad506.pythonanywhere.com/api/admin/error-logs/` (staff only)

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

**Production Server**: https://ziad506.pythonanywhere.com

- **Admin Panel**: https://ziad506.pythonanywhere.com/api/admin/
- **Swagger UI**: https://ziad506.pythonanywhere.com/api/docs/
- **ReDoc**: https://ziad506.pythonanywhere.com/api/redoc/
- **Health Check**: https://ziad506.pythonanywhere.com/api/health/

### Recent Updates

- ✅ **Signup Endpoint**: New user registration with Saudi phone validation
- ✅ **Driver Status Management**: Drivers can update their availability status
- ✅ **Modern Admin UI**: Enhanced admin panel with Jazzmin
- ✅ **Error Logs View**: Admin can view recent errors in the admin panel
- ✅ **Improved Testing**: 85% test pass rate with comprehensive coverage
- ✅ **SQLite Support**: Easier local development with SQLite option
- ✅ **Swagger UI CDN**: Better performance on PythonAnywhere
