@echo off
echo Adding all files to git...
git add .

echo Committing files...
git commit -m "Add missing Streamlit app and documentation files - Add streamlit_app.py: Complete web interface with dashboard - Add SETUP_INSTRUCTIONS.md: Clean repository setup guide - Add SUCCESS_SUMMARY.md: Project completion summary - Ensure all files are properly tracked and pushed"

echo Pushing to GitHub...
git push origin main

echo Done!
pause