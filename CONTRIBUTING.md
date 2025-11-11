# Contributing to RouteX

Thank you for your interest in contributing to RouteX! This document provides guidelines and standards for contributing to the project.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)

---

## Code of Conduct

- Be respectful and professional
- Follow Django and Python best practices
- Write clean, maintainable, well-documented code
- Test thoroughly before submitting changes

---

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Git
- Virtual environment (venv)

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/FatimaaAlzahraa/RouteX.git
cd RouteX

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies
pip install black isort flake8 bandit safety

# Setup environment variables
copy env.example .env
# Edit .env with your configuration

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

---

## Development Workflow

### Branch Strategy

- `main` - Production-ready code
- `develop` - Integration branch for features
- `feature/*` - New features
- `bugfix/*` - Bug fixes
- `hotfix/*` - Critical production fixes

### Creating a Feature Branch

```bash
git checkout develop
git pull origin develop
git checkout -b feature/your-feature-name
```

---

## Coding Standards

### Python Style Guide

We follow **PEP 8** with some project-specific rules:

- **Line length**: 120 characters maximum
- **Indentation**: 4 spaces (no tabs)
- **Imports**: Organized with isort
- **Formatting**: Automated with Black

### Code Quality Tools

Run before committing:

```bash
# Format code
black .
isort .

# Check linting
flake8 .

# Security scan
bandit -r shipments/ users/
safety check
```

### Django Best Practices

1. **Models**

   - Use meaningful field names
   - Add `help_text` to complex fields
   - Create indexes for frequently queried fields
   - Override `__str__()` for better admin display

2. **Views**

   - Keep views thin, logic in services/serializers
   - Use class-based views when appropriate
   - Add docstrings explaining purpose and behavior
   - Handle exceptions gracefully

3. **Serializers**

   - Validate data thoroughly
   - Use custom validation methods
   - Document complex validation logic
   - Keep serializers focused (single responsibility)

4. **Permissions**
   - Use custom permission classes
   - Never bypass authentication
   - Check permissions at view level
   - Log permission failures

### Documentation Standards

Every public function/class must have a docstring:

```python
def calculate_stock_reserve(product: Product, quantity: int) -> bool:
    """
    Reserve stock quantity for a product atomically.

    Args:
        product: Product instance to reserve stock from
        quantity: Number of units to reserve

    Returns:
        True if reservation successful, False if insufficient stock

    Raises:
        ValidationError: If quantity is negative or product inactive
    """
    # Implementation
```

---

## Testing Requirements

### Writing Tests

- **Unit tests**: Test individual functions/methods
- **Integration tests**: Test interactions between components
- **API tests**: Test endpoint behavior and permissions

### Test Structure

```
RouteX/
├── shipments/
│   ├── test_products.py
│   ├── test_shipments.py
│   ├── test_permissions.py
│   └── test_models.py
└── users/
    └── test_authentication.py
```

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest shipments/test_products.py

# Specific test class
pytest shipments/test_products.py::TestProductListCreate

# With coverage
pytest --cov --cov-report=html

# Markers
pytest -m unit
pytest -m api
pytest -m integration
```

### Coverage Requirements

- **Minimum coverage**: 80%
- **New code**: Must have 90%+ coverage
- **Critical paths**: 100% coverage required

### Test Best Practices

```python
@pytest.mark.api
class TestProductCreation:
    """Test product creation endpoint."""

    def test_manager_creates_valid_product(self, manager_client):
        """Manager can create product with valid data."""
        data = {"name": "Product", "price": 100, "stock_qty": 50}
        response = manager_client.post("/api/v1/products/", data)

        assert response.status_code == 201
        assert Product.objects.filter(name="Product").exists()

    def test_driver_cannot_create_product(self, driver_client):
        """Driver is forbidden from creating products."""
        data = {"name": "Product", "price": 100}
        response = driver_client.post("/api/v1/products/", data)

        assert response.status_code == 403
```

---

## Commit Guidelines

### Commit Message Format

```
type(scope): brief description

Detailed explanation if needed.

- Bullet points for multiple changes
- Reference issue numbers: #123
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code formatting (no logic change)
- `refactor`: Code restructuring
- `test`: Adding/updating tests
- `chore`: Build process, dependencies

### Examples

```bash
feat(shipments): add stock reservation on driver assignment

- Reserve product stock when driver is assigned to shipment
- Release stock when driver is removed
- Add tests for stock management edge cases

Closes #42
```

```bash
fix(auth): prevent login for users without role

Users without WarehouseManager or Driver profile should
receive 403 Forbidden instead of defaulting to driver role.

Fixes #38
```

---

## Pull Request Process

### Before Submitting

1. ✅ All tests pass (`pytest`)
2. ✅ Code formatted (`black .` and `isort .`)
3. ✅ No linting errors (`flake8 .`)
4. ✅ Coverage maintained/improved
5. ✅ Documentation updated
6. ✅ Migrations created if needed
7. ✅ `.env.example` updated if new variables added

### PR Checklist

```markdown
## Description

Brief description of changes

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing

- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Manual testing completed

## Checklist

- [ ] Code follows project style guidelines
- [ ] Self-review completed
- [ ] Comments added for complex logic
- [ ] Documentation updated
- [ ] No new warnings introduced
- [ ] Tests pass locally
```

### Review Process

1. Create PR from feature branch to `develop`
2. Automated CI/CD runs (tests, linting, security)
3. At least 1 code review approval required
4. Address review comments
5. Squash and merge once approved

---

## Architecture Guidelines

### Project Structure

```
RouteX/
├── RouteX/              # Django project settings
│   ├── settings.py      # Configuration
│   ├── urls.py          # Root URL routing
│   └── wsgi.py          # WSGI application
├── shipments/           # Shipments app
│   ├── models.py        # Database models
│   ├── serializers.py   # DRF serializers
│   ├── views.py         # API views
│   ├── permissions.py   # Custom permissions
│   ├── urls.py          # App URL routing
│   ├── utils.py         # Helper functions
│   ├── throttling.py    # Rate limiting
│   └── test_*.py        # Tests
├── users/               # Users/auth app
├── conftest.py          # Pytest fixtures
├── pytest.ini           # Pytest configuration
└── requirements.txt     # Python dependencies
```

### Key Principles

1. **Separation of Concerns**: Keep models, views, serializers focused
2. **DRY (Don't Repeat Yourself)**: Extract common logic
3. **SOLID Principles**: Single responsibility, open/closed, etc.
4. **Security First**: Validate input, check permissions, sanitize output
5. **Performance**: Use select_related, prefetch_related, database indexes

---

## Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: Create an issue with reproduction steps
- **Features**: Propose in GitHub Issues first
- **Urgent**: Contact maintainers directly

---

## License

By contributing, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for contributing to RouteX! 🚀
