#!/bin/bash
# Cloud Run デプロイ
set -e

source .env

gcloud run deploy final-tax-return \
    --project "$GCP_PROJECT_ID" \
    --source . \
    --region asia-northeast1 \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 1 \
    --timeout 300 \
    --set-env-vars "SUPABASE_URL=$SUPABASE_URL" \
    --set-env-vars "SUPABASE_ANON_KEY=$SUPABASE_ANON_KEY" \
    --set-env-vars "AUTH_ENABLED=$AUTH_ENABLED" \
    --set-env-vars "GEMINI_API_KEY=$GEMINI_API_KEY"
