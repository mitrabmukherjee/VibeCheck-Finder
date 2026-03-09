@echo off
echo ========================================
echo Loading Full Netflix Dataset
echo ========================================
echo.
echo This will:
echo 1. Convert all 5,850 Netflix items
echo 2. Clear existing data
echo 3. Train new vectorizer
echo 4. Generate embeddings
echo 5. Load into databases
echo.
echo Time: ~3-5 minutes
echo.
pause

cd backend

echo.
echo Step 1/2: Converting Netflix dataset...
python data_pipeline\convert_netflix_dataset.py
if errorlevel 1 (
    echo ERROR: Conversion failed!
    pause
    exit /b 1
)

echo.
echo Step 2/2: Loading into databases...
python data_pipeline\load_full_dataset.py
if errorlevel 1 (
    echo ERROR: Loading failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo SUCCESS! All data loaded.
echo ========================================
echo.
echo Next step: Restart your backend server
echo   1. Stop the current backend (Ctrl+C)
echo   2. Run: python -m uvicorn main:app --reload
echo.
pause
