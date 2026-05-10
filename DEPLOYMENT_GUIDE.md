# Image Upload Integration — Deployment Guide

## Prerequisites

1. **Python Packages** (ensure installed):

   ```bash
   pip install fastapi pydantic httpx python-dotenv
   ```

2. **PHP Database Access** - Ensure your PHP environment can execute migrations

3. **Environment Configuration** (.env in fastapi_ai/):
   ```
   GEMINI_API_KEY=your_api_key_here
   GEMINI_VISION_MODEL=gemini-2.5-flash-lite
   ```

## Step-by-Step Deployment

### 1. Database Migration

Execute the migration to add image_analysis column:

```bash
# From backend_php/ directory
mysql -u root -p mediai_db < migrations/add_image_analysis_to_reports.sql
```

Or execute directly in MySQL:

```sql
ALTER TABLE `triage_reports` ADD COLUMN `image_analysis` LONGTEXT NULL AFTER `explanation`;
CREATE INDEX `idx_image_analysis` ON `triage_reports` (`id`);
```

### 2. Verify Database Schema

```sql
DESC triage_reports;
-- Should show image_analysis column as LONGTEXT NULL
```

### 3. Backend Verification

Ensure FastAPI services are running:

```bash
# Terminal 1: From fastapi_ai/ directory
uvicorn main:app --reload --port 8000
```

Check endpoints are available:

```bash
# Test new endpoint
curl http://localhost:8000/

# Should see "/analyze-symptom-image-for-triage" in endpoints list
```

### 4. Frontend Testing

Open browser and navigate to:

```
http://localhost:3000/frontend/pages/symptom-chat.html
(or your configured frontend URL)
```

### 5. Test Image Upload Flow

1. **Enter a symptom** - E.g., "I have a rash on my arm"
2. **Click "Upload rash, cut, or wound photo"** button
3. **Select an image** - Should show preview with filename and size
4. **Answer follow-up questions** about the symptom
5. **Submit** - Image should be analyzed before report generation
6. **View Report** - Should show:
   - Main triage assessment
   - Image Analysis Results section
   - Visible observations from image
   - Any red flags identified
   - Confidence level

### 6. Verify Report Storage

Check that image analysis is stored:

```sql
SELECT id, possible_condition, image_analysis FROM triage_reports
WHERE user_id = 1
ORDER BY created_at DESC LIMIT 1;
```

Image_analysis should contain JSON data, e.g.:

```json
{
  "image_type": "rash",
  "visible_observations": ["red discoloration", "mild swelling"],
  "red_flags": [],
  "confidence": "medium",
  ...
}
```

## Troubleshooting

### Issue: Image upload button not visible

- **Solution**: Ensure JavaScript is enabled in browser
- **Check**: Open browser console (F12) for JavaScript errors

### Issue: "Image analysis failed" message

- **Check**: Is GEMINI_API_KEY configured?
- **Fallback**: System should use fallback analysis
- **Log**: Check FastAPI console output for errors

### Issue: Image appears to hang during analysis

- **Check**: Network tab in browser DevTools
- **Timeout**: Gemini API calls may take up to 45 seconds
- **Log**: Check FastAPI output for API response times

### Issue: Image analysis not appearing in database

- **Check**: Was database migration applied?
- **Verify**: `SHOW COLUMNS FROM triage_reports;` should show image_analysis
- **Debug**: Check PHP error logs and FastAPI logs

### Issue: Report generation fails with image

- **Check**: Image file size (max 8MB)
- **Verify**: Supported formats (JPG, PNG, WEBP)
- **Test**: Try submitting report without image first
- **Logs**: Check both FastAPI and PHP error logs

## Monitoring

### FastAPI Logs

Look for messages like:

```
"POST /analyze-symptom-image-for-triage" - 200 OK
```

### PHP Logs

Check for successful report creation:

```
INSERT INTO triage_reports ... image_analysis = ...
```

### Browser Console

Check for:

- Image selection success: `"Analyzing your uploaded image..."`
- Report completion: `"Your triage report is ready"`

## Rollback Instructions

If you need to rollback:

### 1. Remove database column (if needed)

```sql
ALTER TABLE `triage_reports` DROP COLUMN `image_analysis`;
DROP INDEX `idx_image_analysis` ON `triage_reports`;
```

### 2. Revert JavaScript changes

```bash
git checkout frontend/js/symptom-chat.js
```

### 3. Revert Python files

```bash
git checkout fastapi_ai/
backend_php/api/reports.php
```

## Performance Optimization

### For High-Traffic Systems

1. **Cache image analysis** - Store analysis results locally for similar images
2. **Queue image processing** - Use Celery for async image analysis
3. **Compress storage** - Store only essential fields from image analysis
4. **Archive old reports** - Move reports older than 90 days to archive

### Recommended Configuration

```python
# In fastapi_ai/main.py
MAX_IMAGE_ANALYSIS_CACHE = 1000  # Cache latest 1000 analyses
IMAGE_ANALYSIS_TIMEOUT = 45  # Seconds
```

## Security Hardening

1. **Rate Limiting** - Add rate limiting to `/analyze-symptom-image-for-triage`
2. **File Validation** - Ensure image MIME type verification
3. **Size Limits** - Already set to 8MB, can be reduced
4. **API Keys** - Rotate GEMINI_API_KEY regularly
5. **CORS** - Verify CORS settings in main.py

## Support

For issues or questions:

1. Check FastAPI logs: Look at terminal where uvicorn is running
2. Check PHP logs: Check `error_log` in your PHP configuration
3. Check browser console: F12 → Console tab for JavaScript errors
4. Review this deployment guide for common issues

## Completion Checklist

- [ ] Database migration applied successfully
- [ ] FastAPI server running with new endpoint
- [ ] Image upload button appears in symptom chat
- [ ] Can select and upload test images
- [ ] Image analysis appears in report
- [ ] Report stores with image_analysis data
- [ ] Retrieved reports show image analysis
- [ ] Fallback works without Gemini API
- [ ] Report functionality maintains backward compatibility

## Next Deployment Tasks

1. Monitor system performance with image uploads
2. Gather user feedback on image analysis quality
3. Adjust confidence thresholds if needed
4. Consider implementing image storage for historical reference
5. Plan UI enhancements based on user feedback
