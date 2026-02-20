## Summary
Merging development branch to main with significant improvements including score recalculation fixes, file upload functionality, student page UI updates, and various bug fixes.

## What's Included

### 🔧 Score Recalculation Fix (Resolves #2)
Implemented comprehensive automatic score recalculation system:
- **ViewSet Lifecycle Hooks**: Added hooks to trigger recalculation on:
  - Grade CRUD operations (create, update, delete)
  - Assessment weight changes
  - Learning outcome mapping changes
  - Enrollment management (enroll, unenroll, bulk enroll)
- **Bulk Import Support**: File imports now automatically trigger score recalculation for affected courses
- **Comprehensive Test Suite**: 8 new test cases covering all recalculation scenarios

### 📁 File Upload Feature
- Initial file upload functionality implementation
- Fixed input reset bug after file upload
- Added sample.xlsx and run.bat for testing and deployment
- Fixed fetch-related issues in file handling

### 🎨 Student Page UI Improvements
- Complete UI redesign for student page
- Bug fixes and improvements for better user experience

## Files Changed (26 files, +2537/-719)

**Backend:**
- `backend/student_evaluation_system/evaluation/views.py` - Added lifecycle hooks for score recalculation
- `backend/student_evaluation_system/core/services/file_import.py` - Bulk import with automatic recalculation
- `backend/student_evaluation_system/evaluation/tests.py` - Comprehensive test suite for recalculation

**Frontend:**
- Student page components - UI updates and bug fixes
- File upload components - New functionality and bug fixes

**Other:**
- `run.bat` - Deployment script
- `sample.xlsx` - Sample data file

## Testing
✅ All tests pass successfully
✅ 8 new test cases for score recalculation

## Related Issues
Resolves #2 - Outcome scores not recalculated after score changes

## Deployment Notes
- No database migrations required
- Changes are backward compatible
- Includes deployment script (run.bat) for easy setup