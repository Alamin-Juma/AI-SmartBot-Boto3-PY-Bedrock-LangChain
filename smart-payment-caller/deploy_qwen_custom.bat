@echo off
REM Quick Deploy Script: Qwen2.5-Coder-7B to Bedrock Custom Import (Windows)
REM Usage: deploy_qwen_custom.bat

echo.
echo ============================================
echo Qwen2.5-Coder-7B Custom Model Deployment
echo ============================================
echo.

REM Get AWS account info
for /f "tokens=*" %%i in ('aws sts get-caller-identity --query Account --output text') do set AWS_ACCOUNT_ID=%%i
if not defined AWS_REGION set AWS_REGION=us-east-1

echo Configuration:
echo    AWS Account: %AWS_ACCOUNT_ID%
echo    AWS Region: %AWS_REGION%
echo.

REM Step 1: Create S3 bucket
echo [Step 1/7] Creating S3 bucket...
set BUCKET_NAME=payment-bot-custom-models-%AWS_ACCOUNT_ID%
aws s3 mb s3://%BUCKET_NAME% --region %AWS_REGION% 2>nul
if %errorlevel%==0 (
    echo    Created bucket: %BUCKET_NAME%
) else (
    echo    Bucket already exists: %BUCKET_NAME%
)

REM Step 2: Download model
echo.
echo [Step 2/7] Downloading Qwen model from Hugging Face...
echo    This will take 10-20 minutes (15GB download)...

if exist "qwen-2.5-coder-7b" (
    echo    Model already downloaded, skipping...
) else (
    echo import os > download_qwen.py
    echo from huggingface_hub import snapshot_download >> download_qwen.py
    echo. >> download_qwen.py
    echo os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1" >> download_qwen.py
    echo hf_model_id = "Qwen/Qwen2.5-Coder-7B-Instruct" >> download_qwen.py
    echo local_directory = "./qwen-2.5-coder-7b" >> download_qwen.py
    echo. >> download_qwen.py
    echo print^(f"Downloading {hf_model_id}..."^) >> download_qwen.py
    echo snapshot_download^( >> download_qwen.py
    echo     repo_id=hf_model_id, >> download_qwen.py
    echo     local_dir=local_directory, >> download_qwen.py
    echo     local_dir_use_symlinks=False >> download_qwen.py
    echo ^) >> download_qwen.py
    echo print^("Download complete!"^) >> download_qwen.py
    
    python download_qwen.py
    echo    Model downloaded to ./qwen-2.5-coder-7b
)

REM Step 3: Upload to S3
echo.
echo [Step 3/7] Uploading model to S3...
echo    This will take 15-30 minutes (15GB upload)...
aws s3 sync qwen-2.5-coder-7b s3://%BUCKET_NAME%/qwen-2.5-coder-7b/ --storage-class INTELLIGENT_TIERING --only-show-errors
echo    Model uploaded to S3

REM Step 4: Create IAM role
echo.
echo [Step 4/7] Creating IAM role for Bedrock...

REM Create trust policy
echo { > bedrock-trust-policy.json
echo   "Version": "2012-10-17", >> bedrock-trust-policy.json
echo   "Statement": [ >> bedrock-trust-policy.json
echo     { >> bedrock-trust-policy.json
echo       "Effect": "Allow", >> bedrock-trust-policy.json
echo       "Principal": { >> bedrock-trust-policy.json
echo         "Service": "bedrock.amazonaws.com" >> bedrock-trust-policy.json
echo       }, >> bedrock-trust-policy.json
echo       "Action": "sts:AssumeRole", >> bedrock-trust-policy.json
echo       "Condition": { >> bedrock-trust-policy.json
echo         "StringEquals": { >> bedrock-trust-policy.json
echo           "aws:SourceAccount": "%AWS_ACCOUNT_ID%" >> bedrock-trust-policy.json
echo         }, >> bedrock-trust-policy.json
echo         "ArnEquals": { >> bedrock-trust-policy.json
echo           "aws:SourceArn": "arn:aws:bedrock:%AWS_REGION%:%AWS_ACCOUNT_ID%:model-import-job/*" >> bedrock-trust-policy.json
echo         } >> bedrock-trust-policy.json
echo       } >> bedrock-trust-policy.json
echo     } >> bedrock-trust-policy.json
echo   ] >> bedrock-trust-policy.json
echo } >> bedrock-trust-policy.json

REM Create S3 policy
echo { > bedrock-s3-policy.json
echo   "Version": "2012-10-17", >> bedrock-s3-policy.json
echo   "Statement": [ >> bedrock-s3-policy.json
echo     { >> bedrock-s3-policy.json
echo       "Effect": "Allow", >> bedrock-s3-policy.json
echo       "Action": [ >> bedrock-s3-policy.json
echo         "s3:GetObject", >> bedrock-s3-policy.json
echo         "s3:ListBucket" >> bedrock-s3-policy.json
echo       ], >> bedrock-s3-policy.json
echo       "Resource": [ >> bedrock-s3-policy.json
echo         "arn:aws:s3:::%BUCKET_NAME%", >> bedrock-s3-policy.json
echo         "arn:aws:s3:::%BUCKET_NAME%/*" >> bedrock-s3-policy.json
echo       ] >> bedrock-s3-policy.json
echo     } >> bedrock-s3-policy.json
echo   ] >> bedrock-s3-policy.json
echo } >> bedrock-s3-policy.json

REM Create role
aws iam create-role --role-name BedrockCustomModelImportRole --assume-role-policy-document file://bedrock-trust-policy.json 2>nul
aws iam put-role-policy --role-name BedrockCustomModelImportRole --policy-name BedrockS3Access --policy-document file://bedrock-s3-policy.json

set ROLE_ARN=arn:aws:iam::%AWS_ACCOUNT_ID%:role/BedrockCustomModelImportRole
echo    Role ARN: %ROLE_ARN%
echo    Waiting 10 seconds for IAM propagation...
timeout /t 10 /nobreak >nul

REM Step 5: Import model to Bedrock
echo.
echo [Step 5/7] Importing model to Bedrock...
echo    This will take 30-60 minutes...

for /f "tokens=2 delims==" %%a in ('wmic os get localdatetime /value') do set datetime=%%a
set JOB_NAME=qwen-coder-7b-import-%datetime:~0,8%-%datetime:~8,6%
set MODEL_NAME=qwen-coder-7b-payment-bot
set S3_URI=s3://%BUCKET_NAME%/qwen-2.5-coder-7b/

aws bedrock create-model-import-job --job-name "%JOB_NAME%" --imported-model-name "%MODEL_NAME%" --role-arn "%ROLE_ARN%" --model-data-source "{\"s3DataSource\": {\"s3Uri\": \"%S3_URI%\"}}" --region %AWS_REGION%

echo    Import job started: %JOB_NAME%
echo.
echo    Waiting for import to complete (checking every 2 minutes)...
echo.

:wait_loop
timeout /t 120 /nobreak >nul
for /f "tokens=*" %%i in ('aws bedrock get-model-import-job --job-identifier "%JOB_NAME%" --query status --output text') do set STATUS=%%i
echo    [%time%] Status: %STATUS%

if "%STATUS%"=="Completed" goto import_complete
if "%STATUS%"=="Failed" goto import_failed
goto wait_loop

:import_failed
echo    Import failed!
aws bedrock get-model-import-job --job-identifier "%JOB_NAME%" --query "{Status:status,Message:message,FailureMessage:failureMessage}" --output json
exit /b 1

:import_complete
echo    Model import completed!

REM Step 6: Get model ARN
echo.
echo [Step 6/7] Getting model ARN...
for /f "tokens=*" %%i in ('aws bedrock list-custom-models --query "modelSummaries[?modelName=='%MODEL_NAME%'].modelArn" --output text') do set MODEL_ARN=%%i

if not defined MODEL_ARN (
    echo    Failed to get model ARN
    exit /b 1
)

echo    Model ARN: %MODEL_ARN%
echo %MODEL_ARN% > qwen_model_arn.txt
echo    Saved to: qwen_model_arn.txt

REM Step 7: Create summary
echo.
echo [Step 7/7] Creating deployment summary...

echo ============================================ > qwen_deployment_summary.txt
echo Qwen2.5-Coder-7B Deployment Complete! >> qwen_deployment_summary.txt
echo ============================================ >> qwen_deployment_summary.txt
echo. >> qwen_deployment_summary.txt
echo Deployment Details: >> qwen_deployment_summary.txt
echo    Date:           %date% %time% >> qwen_deployment_summary.txt
echo    AWS Account:    %AWS_ACCOUNT_ID% >> qwen_deployment_summary.txt
echo    AWS Region:     %AWS_REGION% >> qwen_deployment_summary.txt
echo    S3 Bucket:      s3://%BUCKET_NAME%/qwen-2.5-coder-7b/ >> qwen_deployment_summary.txt
echo    IAM Role:       %ROLE_ARN% >> qwen_deployment_summary.txt
echo    Model Name:     %MODEL_NAME% >> qwen_deployment_summary.txt
echo    Model ARN:      %MODEL_ARN% >> qwen_deployment_summary.txt
echo. >> qwen_deployment_summary.txt
echo Next Steps: >> qwen_deployment_summary.txt
echo    1. Update Lambda: >> qwen_deployment_summary.txt
echo       sam build >> qwen_deployment_summary.txt
echo       sam deploy --parameter-overrides BedrockModelId="%MODEL_ARN%" >> qwen_deployment_summary.txt
echo. >> qwen_deployment_summary.txt
echo    2. Test the model: >> qwen_deployment_summary.txt
echo       python test_local.py >> qwen_deployment_summary.txt
echo. >> qwen_deployment_summary.txt
echo    3. Test in Bedrock Console: >> qwen_deployment_summary.txt
echo       https://console.aws.amazon.com/bedrock/ >> qwen_deployment_summary.txt
echo. >> qwen_deployment_summary.txt
echo Cost Estimate (On-Demand): >> qwen_deployment_summary.txt
echo    - Per active minute: ~$0.012 >> qwen_deployment_summary.txt
echo    - 30 test calls: ~$0.72 >> qwen_deployment_summary.txt
echo    - 1000 calls/month: ~$24.00 >> qwen_deployment_summary.txt
echo    - Auto-scales to $0 after 5 min idle >> qwen_deployment_summary.txt

type qwen_deployment_summary.txt
echo.
echo Summary saved to: qwen_deployment_summary.txt
echo.
echo ============================================
echo DEPLOYMENT COMPLETE!
echo ============================================
echo.
echo Next: sam build ^&^& sam deploy --parameter-overrides BedrockModelId="%MODEL_ARN%"
echo.

pause
