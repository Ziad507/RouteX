# 📋 RouteX Project Structure & Documentation

> **تاريخ التحديث:** 12 نوفمبر 2025  
> **الإصدار:** v1.0.0  
> **البيئة:** Django 5.2.6 + DRF + PostgreSQL/SQLite

---

## 📊 نظرة عامة على المشروع

**RouteX** هو نظام إدارة لوجستيات وشحنات متكامل مبني على Django. يدعم النظام دورين رئيسيين:

### 👥 الأدوار (Roles)

1. **🚗 السائق (Driver)**
   - عرض الشحنات المعينة له
   - تحديث حالة الشحنات (ASSIGNED → IN_TRANSIT → DELIVERED)
   - تحديث حالة التوفر (متاح/مشغول)
   - إضافة صور وموقع GPS عند تحديث الحالة

2. **📦 مدير المستودع (Warehouse Manager)**
   - إدارة المنتجات والمخزون
   - إنشاء وإدارة الشحنات
   - تعيين السائقين للشحنات
   - إدارة المستودعات والعملاء
   - مراقبة حالة جميع السائقين والشحنات

---

## 🗂️ هيكل المشروع

```
RouteX/
├── RouteX/                    # المجلد الرئيسي للمشروع
│   ├── settings.py           # إعدادات Django (DB, CORS, Security, JWT)
│   ├── urls.py               # URL الرئيسي (Admin, API Docs)
│   └── wsgi.py               # WSGI للنشر
│
├── users/                     # تطبيق المستخدمين
│   ├── models.py             # CustomUser (username + phone)
│   ├── views.py              # Login, Signup, WhoAmI, DriverStatus
│   ├── urls.py               # /api/v1/auth/* endpoints
│   ├── admin.py              # إدارة المستخدمين + الأدوار (Enhanced UI)
│   └── static/users/css/
│       └── admin.css         # تصميم الأدمن (Modern Gradient Theme)
│
├── shipments/                 # تطبيق الشحنات
│   ├── models.py             # Driver, Manager, Product, Warehouse, Customer, Shipment, StatusUpdate
│   ├── serializers.py        # DRF Serializers لجميع المودلز
│   ├── views.py              # API Views (Products, Shipments, Drivers, etc)
│   ├── urls.py               # /api/v1/* endpoints
│   ├── admin.py              # إدارة شاملة (CRUD + Badges + Quick Actions)
│   ├── permissions.py        # IsDriver, IsWarehouseManager
│   ├── throttling.py         # Custom throttling rates
│   └── signals.py            # Auto-update shipment status on StatusUpdate
│
├── static/                    # ملفات Static (CSS, JS, Images)
│   └── users/css/admin.css   # تصميم الأدمن المخصص
│
├── media/                     # ملفات الرفع (صور المنتجات، صور الحالة)
│   ├── products/             # صور المنتجات
│   └── status_photos/        # صور تحديثات الحالة
│
├── docs/                      # التوثيق
│   └── openapi.json          # OpenAPI 3.0 Schema
│
├── .github/workflows/         # CI/CD
│   ├── ci.yml                # Tests + Linting + Security
│   └── publish-openapi.yml   # Auto-publish to SwaggerHub
│
├── requirements.txt           # جميع المكتبات المطلوبة
├── pytest.ini                # إعدادات الاختبارات
├── conftest.py               # Pytest fixtures
├── env.example               # قالب ملف البيئة
└── README.md                 # دليل المستخدم
```

---

## 🗄️ قاعدة البيانات - الموديلز (Models)

### 1. **CustomUser** (`users.models`)
```python
- username: CharField (unique)
- phone: CharField (unique) - رقم سعودي (+966XXXXXXXXX)
- password: Hashed password
```

### 2. **Driver** (`shipments.models`)
```python
- user: OneToOne → CustomUser
- is_active: Boolean (متاح = True, مشغول = False)
- related_name: "driver_profile"
```

### 3. **WarehouseManager** (`shipments.models`)
```python
- user: OneToOne → CustomUser
- related_name: "warehouse_manager_profile"
```

### 4. **Product** (`shipments.models`)
```python
- name: CharField
- price: DecimalField (SAR)
- unit: CharField (KG, لتر, صندوق, etc)
- stock_qty: PositiveIntegerField
- image: ImageField (optional)
- is_active: Boolean
- related_name: "shipments"
```

### 5. **Warehouse** (`shipments.models`)
```python
- name: CharField
- location: CharField
- related_name: "shipments"
```

### 6. **Customer** (`shipments.models`)
```python
- name: CharField
- phone: CharField
- address: CharField (العنوان الأول)
- address2: CharField (العنوان الثاني - اختياري)
- address3: CharField (العنوان الثالث - اختياري)
- related_name: "shipments"
```

### 7. **Shipment** (`shipments.models`)
```python
- product: ForeignKey → Product
- warehouse: ForeignKey → Warehouse
- driver: ForeignKey → Driver (nullable)
- customer: ForeignKey → Customer
- customer_address: CharField (العنوان المختار من عناوين العميل)
- notes: TextField (optional)
- current_status: CharField (NEW, ASSIGNED, IN_TRANSIT, DELIVERED)
- assigned_at: DateTime
- created_at, updated_at: DateTime
```

### 8. **StatusUpdate** (`shipments.models`)
```python
- shipment: ForeignKey → Shipment
- status: CharField (choices من ShipmentStatus)
- timestamp: DateTime
- note: TextField (optional)
- photo: ImageField (optional)
- latitude, longitude: DecimalField (GPS - optional)
- location_accuracy_m: PositiveInt (دقة GPS بالأمتار - optional)
```

---

## 🔌 API Endpoints

### **Authentication (Public)**
```
POST   /api/v1/auth/signup/      - تسجيل مستخدم جديد (Driver بشكل افتراضي)
POST   /api/v1/auth/login/       - تسجيل الدخول (JWT tokens)
POST   /api/v1/auth/refresh/     - تجديد Access Token
GET    /api/v1/auth/whoami/      - معلومات المستخدم الحالي + دوره
```

### **Driver Endpoints (IsDriver Permission)**
```
GET    /api/v1/driver/shipments/     - عرض الشحنات المعينة للسائق
POST   /api/v1/status-updates/       - تحديث حالة الشحنة + صورة + GPS
GET    /api/v1/driver/status/        - عرض حالة السائق (متاح/مشغول)
PATCH  /api/v1/driver/status/        - تحديث حالة السائق
```

### **Manager Endpoints (IsWarehouseManager Permission)**
```
# Products
GET    /api/v1/products/             - قائمة المنتجات
POST   /api/v1/products/             - إضافة منتج جديد
GET    /api/v1/products/<id>/        - تفاصيل منتج
PUT    /api/v1/products/<id>/        - تعديل منتج
DELETE /api/v1/products/<id>/        - حذف منتج

# Shipments
GET    /api/v1/manager/shipments/    - قائمة جميع الشحنات
POST   /api/v1/shipments/            - إنشاء شحنة جديدة
GET    /api/v1/shipments/<id>/       - تفاصيل شحنة
PUT    /api/v1/shipments/<id>/       - تعديل شحنة
DELETE /api/v1/shipments/<id>/       - حذف شحنة

# Warehouses
GET    /api/v1/warehouses/           - قائمة المستودعات
POST   /api/v1/warehouses/           - إضافة مستودع
GET    /api/v1/warehouses/<id>/      - تفاصيل مستودع
PUT    /api/v1/warehouses/<id>/      - تعديل مستودع
DELETE /api/v1/warehouses/<id>/      - حذف مستودع

# Customers
GET    /api/v1/customers/            - قائمة العملاء
POST   /api/v1/customers/            - إضافة عميل
GET    /api/v1/customers/<id>/       - تفاصيل عميل
PUT    /api/v1/customers/<id>/       - تعديل عميل
DELETE /api/v1/customers/<id>/       - حذف عميل
GET    /api/v1/customers/<id>/addresses/ - عناوين العميل

# Drivers
GET    /api/v1/drivers/              - قائمة جميع السائقين + حالتهم
GET    /api/v1/drivers/<id>/         - تفاصيل سائق
DELETE /api/v1/drivers/<id>/         - حذف سائق

# Autocomplete
GET    /api/v1/autocomplete/customers/  - بحث سريع عن عميل
GET    /api/v1/autocomplete/shipments/  - بحث سريع عن شحنة
```

### **API Documentation (Public)**
```
GET    /api/docs/          - Swagger UI (Interactive)
GET    /api/redoc/         - ReDoc (Clean documentation)
GET    /api/schema/        - OpenAPI 3.0 JSON Schema
```

---

## 🎨 Admin Panel - التحسينات

### **الوصول**
```
URL: https://ziad506.pythonanywhere.com/api/admin/
```

### **المميزات المضافة**

#### 1. **Users (CustomUser) Admin**
- ✅ إدارة الأدوار بالكامل (Driver, Manager)
- ✅ Inline forms لإضافة/حذف الأدوار مباشرة
- ✅ Badges ملونة لعرض الدور والحالة
- ✅ عداد الشحنات لكل سائق
- ✅ Bulk Actions (تعيين/إزالة أدوار - تفعيل/تعطيل)
- ✅ Quick Actions (تعديل - عرض الشحنات)

#### 2. **Driver Admin**
- ✅ عرض حالة السائق (Available/Busy) مع badges ملونة
- ✅ عداد الشحنات (Total + Active)
- ✅ Bulk Actions (تغيير الحالة)
- ✅ Form validation (منع تعارض الأدوار)

#### 3. **Product Admin**
- ✅ عرض السعر والمخزون مع badges ملونة
- ✅ معاينة الصورة في القائمة
- ✅ تحذير للمنتجات قليلة المخزون
- ✅ Bulk Actions (تفعيل/تعطيل)

#### 4. **Warehouse Admin**
- ✅ عداد الشحنات لكل مستودع
- ✅ Quick links لعرض الشحنات

#### 5. **Customer Admin**
- ✅ عرض عدد العناوين المحفوظة
- ✅ عداد الشحنات
- ✅ تحذير للعملاء بدون عناوين

#### 6. **Shipment Admin**
- ✅ Smart address selection (اختيار من عناوين العميل فقط)
- ✅ Form validation للعناوين
- ✅ Status badges ملونة
- ✅ معلومات السائق + حالته
- ✅ Quick links للـ status updates
- ✅ Bulk Actions (تعيين - تسليم - إلغاء)

#### 7. **StatusUpdate Admin**
- ✅ Timeline view للتحديثات
- ✅ GPS location مع رابط Google Maps
- ✅ Status badges
- ✅ Quick link للشحنة

### **التصميم (Custom CSS)**
- 🎨 Modern gradient background (Dark blue to Sky blue)
- 🎨 Glassmorphism panels مع blur effects
- 🎨 Animated buttons and hover effects
- 🎨 Color-coded badges (Green=Active, Red=Inactive, Blue=Manager)
- 🎨 Responsive design
- 🎨 Jazzmin theme مع تخصيصات

---

## 🔐 الأمان (Security)

### **Authentication**
- JWT tokens (Access: 12h, Refresh: 7 days)
- Password hashing (Django's default)
- Phone number validation (Saudi format)

### **Permissions**
- `IsDriver` - للسائقين فقط
- `IsWarehouseManager` - لمديري المستودعات فقط
- Custom permission classes في `shipments.permissions`

### **CORS**
- Development: Allow all localhost
- Production: Explicit whitelist via `CORS_ALLOWED_ORIGINS`
- Support for preflight requests (OPTIONS)
- Regex support for localhost:any-port

### **Production Security (when DEBUG=False)**
- HSTS enabled (1 year)
- Secure cookies (HTTPOnly, Secure, SameSite)
- SSL redirect
- CSP headers
- X-Frame-Options: DENY

### **Rate Limiting**
```python
"anon": "100/hour"       # غير مسجلين
"user": "2000/hour"      # مسجلين
"driver": "5000/hour"    # سائقين
"manager": "10000/hour"  # مديرين
```

---

## 🧪 الاختبارات (Testing)

### **الملفات**
```
users/test_authentication.py   - اختبار Login
users/test_signup.py            - اختبار Signup
users/test_driver_status.py    - اختبار تحديث حالة السائق
shipments/test_products.py     - اختبار المنتجات
shipments/test_shipments.py    - اختبار الشحنات
shipments/test_driver_management.py - اختبار إدارة السائقين
```

### **التشغيل**
```bash
# جميع الاختبارات
pytest

# مع Coverage
pytest --cov --cov-report=html

# اختبار محدد
pytest users/test_signup.py

# بحسب Marker
pytest -m api
pytest -m unit
```

### **التغطية (Coverage)**
- الهدف: >80%
- HTML Report: `htmlcov/index.html`

---

## 🚀 النشر (Deployment)

### **البيئة الحالية**
- **Platform:** PythonAnywhere
- **URL:** https://ziad506.pythonanywhere.com
- **Database:** SQLite (للاختبار) / PostgreSQL (للإنتاج)

### **المتغيرات المطلوبة (.env)**
```env
DJANGO_SECRET_KEY=<strong-secret-key>
DEBUG=False
USE_SQLITE=False
DB_NAME=routex_production
DB_USER=routex_user
DB_PASSWORD=<password>
DB_HOST=<host>
DB_PORT=5432
CORS_ALLOWED_ORIGINS=https://yourdomain.com
CORS_ALLOW_LOCALHOST=True
ALLOWED_HOSTS=.pythonanywhere.com
```

### **الأوامر على PythonAnywhere**
```bash
# التحديث من GitHub
git pull origin main

# تثبيت المكتبات
pip install -r requirements.txt

# تطبيق Migrations
python manage.py migrate --noinput

# جمع Static files
python manage.py collectstatic --noinput

# إعادة تحميل Web App
# من Web tab → Reload button
```

---

## 📊 سير العمل (Workflow)

### **1. مدير المستودع يبدأ:**
```
1. إنشاء منتجات (Products)
2. إنشاء مستودعات (Warehouses)
3. إنشاء عملاء مع عناوينهم (Customers + Addresses)
4. إنشاء مستخدمين سائقين (Users → Assign Driver role)
5. إنشاء شحنات (Shipments) → اختيار:
   - المنتج
   - المستودع
   - العميل + العنوان
   - السائق (optional)
```

### **2. السائق يتسلم:**
```
1. تسجيل الدخول → GET /api/v1/auth/login/
2. عرض الشحنات → GET /api/v1/driver/shipments/
3. تحديث الحالة → POST /api/v1/status-updates/
   - ASSIGNED → "تم الاستلام"
   - IN_TRANSIT → "في الطريق" + صورة + GPS
   - DELIVERED → "تم التسليم" + صورة + توقيع العميل
4. تحديث حالة التوفر → PATCH /api/v1/driver/status/
   - is_active = False → "مشغول"
   - is_active = True → "متاح"
```

### **3. مدير المستودع يراقب:**
```
1. عرض جميع الشحنات → GET /api/v1/manager/shipments/
2. عرض حالة السائقين → GET /api/v1/drivers/
   - يعرض is_active + status + عدد الشحنات
3. Admin Panel → إحصائيات شاملة
```

---

## 🐛 المشاكل المحلولة

### **1. Database Connection**
- **المشكلة:** PostgreSQL connection refused
- **الحل:** SQLite fallback للتطوير المحلي

### **2. CORS Errors**
- **المشكلة:** Frontend (localhost) لا يستطيع الاتصال
- **الحل:** `CORS_ALLOW_LOCALHOST` + Regex لأي port

### **3. Admin Errors**
- **المشكلة:** `AttributeError` في `get_actions`
- **الحل:** تغيير اسم الدالة إلى `get_quick_actions`

- **المشكلة:** `FieldError: 'shipment'` في annotations
- **الحل:** استخدام `Count('shipments')` (الاسم الصحيح)

- **المشكلة:** `ValueError` في `format_html` للسعر
- **الحل:** Format السعر أولاً ثم تمريره

### **4. Schema Generation**
- **المشكلة:** `drf-spectacular` لا يستطيع تخمين serializer
- **الحل:** استخدام `inline_serializer` في `@extend_schema`

### **5. Test Failures**
- **المشكلة:** `TypeError: Cannot encode None for key 'driver'`
- **الحل:** `TEST_REQUEST_DEFAULT_FORMAT = "json"`

---

## 📝 ملاحظات مهمة

### **1. علاقات الموديلز**
```
User ←1:1→ Driver ←1:N→ Shipment
User ←1:1→ WarehouseManager
Product ←1:N→ Shipment
Warehouse ←1:N→ Shipment
Customer ←1:N→ Shipment
Shipment ←1:N→ StatusUpdate
```

### **2. التحديث التلقائي**
- عند إنشاء `StatusUpdate` → يتم تحديث `Shipment.current_status` تلقائياً (via Signal)

### **3. Stock Management**
- حالياً: لا يوجد خصم تلقائي من المخزون
- يمكن إضافته في `Shipment.save()` أو Signal

### **4. الصور (Images)**
- Max size: 5MB
- Allowed: JPG, JPEG, PNG, WebP
- Products → `/media/products/`
- Status → `/media/status_photos/`

### **5. الوقت (Timezone)**
- Timezone: `Asia/Riyadh`
- Format: `2025-11-12 4:03PM` (12-hour)

---

## 🔧 التطوير المستقبلي

### **مقترحات:**
- [ ] Real-time notifications (WebSockets)
- [ ] Push notifications للسائقين
- [ ] Route optimization (Google Maps API)
- [ ] Advanced analytics dashboard
- [ ] Multi-language support (Arabic + English)
- [ ] Export reports (PDF, Excel)
- [ ] Automatic stock deduction
- [ ] Driver earnings tracking
- [ ] Customer rating system
- [ ] Email/SMS notifications

---

## 📞 الدعم

- **GitHub:** https://github.com/FatimaaAlzahraa/RouteX
- **API Docs:** https://ziad506.pythonanywhere.com/api/docs/
- **Admin:** https://ziad506.pythonanywhere.com/api/admin/

---

**آخر تحديث:** 12 نوفمبر 2025  
**المطورين:** Origami Techs Team

