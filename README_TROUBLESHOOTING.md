# Troubleshooting Guide for 404 API Errors

## Issue: API Request failed: Error: API Error: 404 Not Found

This error typically occurs when the Django backend server is not running or there are missing data records.

### Step 1: Start the Django Backend Server

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Activate the virtual environment (if using one):
   ```bash
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Start the Django development server:
   ```bash
   python manage.py runserver
   ```

4. Verify the server is running by visiting: http://localhost:8000/admin/

### Step 2: Add Sample Data

If the server is running but you're still getting 404 errors, you need to add sample data:

1. **Add sample customers:**
   ```bash
   python add_sample_categories.py
   python add_sample_products.py
   python add_sample_team_members.py
   ```

2. **Add sample sales pipeline data:**
   ```bash
   python add_sample_sales_pipeline.py
   ```

3. **Verify data was created:**
   ```bash
   python manage.py shell
   ```
   ```python
   from apps.sales.models import SalesPipeline
   from apps.clients.models import Client
   print(f"Pipelines: {SalesPipeline.objects.count()}")
   print(f"Clients: {Client.objects.count()}")
   ```

### Step 3: Check Authentication

1. **Login to the frontend** with valid credentials
2. **Check browser console** for authentication token issues
3. **Verify the token is being sent** in API requests

### Step 4: Test API Endpoints

1. **Test the pipeline endpoint directly:**
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" http://localhost:8000/api/sales/pipeline/1/
   ```

2. **Check Django logs** for any errors:
   ```bash
   python manage.py runserver --verbosity=2
   ```

### Step 5: Common Issues and Solutions

#### Issue: "No tenant found"
**Solution:** Create a tenant first:
```bash
python manage.py shell
```
```python
from apps.tenants.models import Tenant
tenant = Tenant.objects.create(name="Test Tenant", domain="test.com")
```

#### Issue: "No customers found"
**Solution:** Run the customer creation script:
```bash
python add_sample_categories.py
```

#### Issue: CORS errors
**Solution:** Check CORS settings in `core/settings.py`:
```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
```

#### Issue: Database connection errors
**Solution:** Check database settings and ensure PostgreSQL is running:
```bash
python manage.py check
python manage.py migrate
```

### Step 6: Verify Frontend Configuration

1. **Check API base URL** in `jewellery-crm/src/lib/api-service.ts`:
   ```typescript
   const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
   ```

2. **Ensure environment variables** are set correctly in `.env.local`:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000/api
   ```

### Step 7: Debug API Calls

1. **Open browser developer tools**
2. **Go to Network tab**
3. **Try to access a pipeline**
4. **Check the actual URL being called**
5. **Verify the response status and headers**

### Quick Fix Script

Run this script to set up everything:
```bash
cd backend
python manage.py migrate
python add_sample_categories.py
python add_sample_products.py
python add_sample_team_members.py
python add_sample_sales_pipeline.py
python manage.py runserver
```

Then start the frontend:
```bash
cd ../jewellery-crm
npm run dev
```

### Still Having Issues?

1. **Check Django logs** for detailed error messages
2. **Verify all URLs** are properly configured in `core/urls.py`
3. **Test with a simple API call** using curl or Postman
4. **Check if the specific pipeline ID exists** in the database 