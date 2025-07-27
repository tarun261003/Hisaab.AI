@echo off
echo 🚀 Deploying HisabAgent with CORS support to Google Cloud Run...

REM Escape the internal double quotes for batch file (use ^")
gcloud run deploy hisaabai-service ^
  --source=temp_staging ^
  --region=africa-south1 ^
  --project=hisabai-edde7 ^
  --memory=1Gi ^
  --allow-unauthenticated ^

if %ERRORLEVEL% EQU 0 (
    echo ✅ Deployment successful!
    echo 🔗 Service URL: https://hisaabai-service-174268603299.africa-south1.run.app
) else (
    echo ❌ Deployment failed with error code %ERRORLEVEL%
)

pause


