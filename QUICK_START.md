# ⚡ دليل البدء السريع - RouteX

> **للرجوع السريع أثناء العمل**

---

## 🎯 الأساسيات

### **ما هو RouteX؟**
نظام إدارة شحنات يدعم دورين:
- 🚗 **سائق:** يستلم شحنات ويحدث حالتها
- 📦 **مدير مستودع:** يدير كل شيء (منتجات، شحنات، سائقين، عملاء)

---

## 🔑 بيانات الوصول

### **Admin Panel:**
```
URL: https://ziad506.pythonanywhere.com/api/admin/
Username: (اسم المستخدم)
Password: (كلمة المرور)
```

### **API Documentation:**
```
Swagger UI: https://ziad506.pythonanywhere.com/api/docs/
ReDoc:      https://ziad506.pythonanywhere.com/api/redoc/
```

---

## 📋 سير العمل السريع

### **للمدير:**
```
1. أضف منتجات        → Admin → Products → Add
2. أضف مستودعات       → Admin → Warehouses → Add
3. أضف عملاء + عناوين → Admin → Customers → Add
4. أضف سائقين         → Admin → Users → Add → Assign Driver role
5. أنشئ شحنة          → Admin → Shipments → Add
   - اختر: منتج، مستودع، عميل، عنوان، سائق
6. راقب الحالة        → Admin → Drivers (حالة السائقين)
                        → Admin → Shipments (حالة الشحنات)
```

### **للسائق (API):**
```
1. Login:
   POST /api/v1/auth/login/
   Body: {"phone": "966500000013", "password": "pass"}

2. عرض الشحنات:
   GET /api/v1/driver/shipments/
   Headers: Authorization: Bearer <token>

3. تحديث الحالة:
   POST /api/v1/status-updates/
   Body: {
     "shipment": 1,
     "status": "IN_TRANSIT",
     "note": "في الطريق",
     "latitude": 24.7136,
     "longitude": 46.6753
   }

4. تحديث حالة التوفر:
   PATCH /api/v1/driver/status/
   Body: {"is_active": false}  // مشغول
```

---

## 🚀 النشر السريع على PythonAnywhere

### **الطريقة السريعة (Git):**
```bash
# 1. Commit محلياً
git add .
git commit -m "Update"
git push

# 2. على PythonAnywhere Console
cd ~/RouteX
git pull
python manage.py collectstatic --noinput

# 3. Web tab → Reload
```

### **الملفات المحدثة:**
```
✅ users/admin.py
✅ shipments/admin.py
✅ users/static/users/css/admin.css
✅ RouteX/settings.py
```

---

## 🐛 حل المشاكل السريع

### **Admin لا يفتح (500 error):**
```bash
# تحقق من Error log في Web tab
# ثم:
cd ~/RouteX
python manage.py check
```

### **التصميم لا يظهر:**
```bash
cd ~/RouteX
python manage.py collectstatic --noinput --clear
# ثم Reload من Web tab
```

### **CORS error:**
```env
# في .env على PythonAnywhere:
CORS_ALLOW_LOCALHOST=True
```

---

## 🎨 المميزات الرئيسية في Admin

### **Users:**
- ✅ إدارة أدوار (Driver/Manager inline)
- ✅ Badges ملونة للحالات
- ✅ Bulk actions (تعيين أدوار)

### **Drivers:**
- ✅ حالة السائق (Available/Busy)
- ✅ عداد الشحنات
- ✅ Toggle availability

### **Products:**
- ✅ Stock badges (In Stock/Low/Out)
- ✅ Image preview
- ✅ Price display

### **Shipments:** ⭐
- ✅ **Smart address selection**
- ✅ Status badges
- ✅ Driver status display
- ✅ Form validation
- ✅ Quick links

### **Customers:**
- ✅ Address counter
- ✅ عدد الشحنات

### **StatusUpdate:**
- ✅ GPS links (Google Maps)
- ✅ Timeline view

---

## 📱 الاختبار السريع

### **Checklist:**
- [ ] افتح Admin → ✅ يعمل
- [ ] أضف مستخدم → ✅ يعمل
- [ ] عين دور Driver → ✅ يعمل
- [ ] أضف شحنة → ✅ Smart address يعمل
- [ ] تحقق من Badges → ✅ ألوان صحيحة
- [ ] جرب Quick Actions → ✅ تعمل
- [ ] جرب Bulk Actions → ✅ تعمل

---

## 📞 روابط سريعة

| الصفحة | الرابط |
|--------|--------|
| Admin Home | `/api/admin/` |
| Users | `/api/admin/users/customuser/` |
| Drivers | `/api/admin/shipments/driver/` |
| Products | `/api/admin/shipments/product/` |
| Shipments | `/api/admin/shipments/shipment/` |
| Customers | `/api/admin/shipments/customer/` |
| API Docs | `/api/docs/` |

---

## 📚 ملفات التوثيق الكاملة

```
README.md              - دليل شامل
PROJECT_STRUCTURE.md   - بنية المشروع
ADMIN_CHECKLIST.md     - اختبار الأدمن
DEPLOYMENT_GUIDE.md    - دليل النشر
SUMMARY.md            - ملخص شامل
QUICK_START.md        - هذا الملف
```

---

## ✅ الحالة الحالية

```
✅ API: جاهز 100%
✅ Admin: جاهز 100%
✅ Tests: جاهزة 100%
✅ Documentation: جاهزة 100%
✅ Deployment: جاهز 100%

المشروع جاهز للإنتاج! 🎉
```

---

**تم بحمد الله!**

