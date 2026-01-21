-- =============================================================
-- 確定申告収支記録アプリケーション - Supabase 初期スキーマ
-- =============================================================
-- このSQLをSupabase SQL Editorで実行してください
-- https://supabase.com/dashboard/project/YOUR_PROJECT/sql

-- =============================================================
-- 1. テーブル作成
-- =============================================================

-- カテゴリテーブル（ユーザーごとにカスタマイズ可能）
CREATE TABLE IF NOT EXISTS categories (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    type TEXT NOT NULL CHECK (type IN ('income', 'expense')),
    name TEXT NOT NULL,
    display_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, type, name)
);

-- 収支記録テーブル
CREATE TABLE IF NOT EXISTS records (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('income', 'expense')),
    category TEXT NOT NULL,
    client TEXT DEFAULT '',
    description TEXT DEFAULT '',
    currency TEXT DEFAULT 'JPY' CHECK (currency IN ('JPY', 'USD')),
    amount_original NUMERIC NOT NULL,
    ttm NUMERIC,
    amount_jpy NUMERIC NOT NULL,
    withholding_tax BOOLEAN DEFAULT FALSE,
    withholding_amount NUMERIC DEFAULT 0,
    proration BOOLEAN DEFAULT FALSE,
    proration_rate NUMERIC DEFAULT 100,
    amount_prorated NUMERIC NOT NULL,
    attachment_path TEXT,
    fiscal_year INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 設定テーブル（ユーザー別）
CREATE TABLE IF NOT EXISTS settings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    key TEXT NOT NULL,
    value TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, key)
);

-- =============================================================
-- 2. インデックス作成
-- =============================================================

CREATE INDEX IF NOT EXISTS idx_records_user_id ON records(user_id);
CREATE INDEX IF NOT EXISTS idx_records_fiscal_year ON records(fiscal_year);
CREATE INDEX IF NOT EXISTS idx_records_type ON records(type);
CREATE INDEX IF NOT EXISTS idx_records_date ON records(date);
CREATE INDEX IF NOT EXISTS idx_records_category ON records(category);
CREATE INDEX IF NOT EXISTS idx_settings_user_id ON settings(user_id);
CREATE INDEX IF NOT EXISTS idx_categories_user_id ON categories(user_id);
CREATE INDEX IF NOT EXISTS idx_categories_type ON categories(type);

-- =============================================================
-- 3. Row Level Security (RLS) 設定
-- =============================================================

-- RLSを有効化
ALTER TABLE records ENABLE ROW LEVEL SECURITY;
ALTER TABLE settings ENABLE ROW LEVEL SECURITY;

-- recordsテーブルのポリシー
-- ユーザーは自分のデータのみ参照可能
CREATE POLICY "Users can view their own records"
    ON records FOR SELECT
    USING (auth.uid() = user_id);

-- ユーザーは自分のデータのみ作成可能
CREATE POLICY "Users can insert their own records"
    ON records FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- ユーザーは自分のデータのみ更新可能
CREATE POLICY "Users can update their own records"
    ON records FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- ユーザーは自分のデータのみ削除可能
CREATE POLICY "Users can delete their own records"
    ON records FOR DELETE
    USING (auth.uid() = user_id);

-- settingsテーブルのポリシー
CREATE POLICY "Users can view their own settings"
    ON settings FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own settings"
    ON settings FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own settings"
    ON settings FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own settings"
    ON settings FOR DELETE
    USING (auth.uid() = user_id);

-- categoriesテーブルのポリシー（ユーザーごと）
ALTER TABLE categories ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own categories"
    ON categories FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own categories"
    ON categories FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own categories"
    ON categories FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own categories"
    ON categories FOR DELETE
    USING (auth.uid() = user_id);

-- =============================================================
-- 4. 初期データ
-- =============================================================
-- カテゴリはユーザーごとに管理されるため、初期データは不要
-- アプリケーション側で新規ユーザーにデフォルトカテゴリを作成

-- =============================================================
-- 5. updated_at自動更新用トリガー
-- =============================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_records_updated_at
    BEFORE UPDATE ON records
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_settings_updated_at
    BEFORE UPDATE ON settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================
-- 6. Storage バケット設定
-- =============================================================
-- 注意: バケット作成はDashboardから行う必要があります
-- Supabase Dashboard > Storage > New bucket
-- - Bucket name: attachments
-- - Public bucket: OFF (private)
-- - File size limit: 10MB
-- - Allowed MIME types: image/jpeg, image/png, application/pdf, image/gif

-- Storage RLS ポリシー
-- ファイルパス構造: {user_id}/{fiscal_year}/{filename}
-- ユーザーは自分のディレクトリ配下のみアクセス可能

-- SELECT: ユーザーは自分のファイルのみ閲覧可能
CREATE POLICY "Users can view own attachments"
    ON storage.objects FOR SELECT
    USING (
        bucket_id = 'attachments'
        AND auth.uid()::text = (storage.foldername(name))[1]
    );

-- INSERT: ユーザーは自分のディレクトリにのみアップロード可能
CREATE POLICY "Users can upload to own directory"
    ON storage.objects FOR INSERT
    WITH CHECK (
        bucket_id = 'attachments'
        AND auth.uid()::text = (storage.foldername(name))[1]
    );

-- UPDATE: ユーザーは自分のファイルのみ更新可能
CREATE POLICY "Users can update own attachments"
    ON storage.objects FOR UPDATE
    USING (
        bucket_id = 'attachments'
        AND auth.uid()::text = (storage.foldername(name))[1]
    )
    WITH CHECK (
        bucket_id = 'attachments'
        AND auth.uid()::text = (storage.foldername(name))[1]
    );

-- DELETE: ユーザーは自分のファイルのみ削除可能
CREATE POLICY "Users can delete own attachments"
    ON storage.objects FOR DELETE
    USING (
        bucket_id = 'attachments'
        AND auth.uid()::text = (storage.foldername(name))[1]
    );
