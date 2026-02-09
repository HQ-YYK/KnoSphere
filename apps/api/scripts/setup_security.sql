-- KnoSphere 企业级安全配置脚本
-- 行级安全 (RLS) 配置

-- 1. 为用户表添加额外安全字段（如果不存在）
ALTER TABLE "users" ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true;
ALTER TABLE "users" ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "users" ADD COLUMN IF NOT EXISTS last_login TIMESTAMP;
ALTER TABLE "users" ADD COLUMN IF NOT EXISTS permissions JSONB DEFAULT '{"documents": ["read", "write", "delete"], "admin": false}'::jsonb;

-- 2. 为文档表添加安全字段（如果不存在）
ALTER TABLE documents ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT false;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}';
ALTER TABLE documents ADD COLUMN IF NOT EXISTS access_control JSONB DEFAULT '{"read": [], "write": [], "delete": []}'::jsonb;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES "users"(id);

-- 3. 启用行级安全
ALTER TABLE "users" ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

-- 4. 为用户表创建安全策略
-- 先删除可能存在的策略
DROP POLICY IF EXISTS user_select_own ON "users";
DROP POLICY IF EXISTS user_update_own ON "users";
DROP POLICY IF EXISTS user_select_admin ON "users";

-- 策略1: 用户只能查看自己的信息
CREATE POLICY user_select_own ON "users"
    FOR SELECT
    USING (id::text = current_setting('app.current_user_id', true));

-- 策略2: 用户只能更新自己的信息
CREATE POLICY user_update_own ON "users"
    FOR UPDATE
    USING (id::text = current_setting('app.current_user_id', true));

-- 策略3: 管理员可以查看所有用户
CREATE POLICY user_select_admin ON "users"
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM "users" u 
            WHERE u.id::text = current_setting('app.current_user_id', true)
            AND (u.permissions->>'admin')::boolean = true
        )
    );

-- 5. 为文档表创建安全策略
-- 先删除可能存在的策略
DROP POLICY IF EXISTS document_select_user ON documents;
DROP POLICY IF EXISTS document_insert_user ON documents;
DROP POLICY IF EXISTS document_update_user ON documents;
DROP POLICY IF EXISTS document_delete_user ON documents;
DROP POLICY IF EXISTS document_admin_all ON documents;

-- 策略1: 用户可以查看自己的文档和公开文档
CREATE POLICY document_select_user ON documents
    FOR SELECT
    USING (
        user_id::text = current_setting('app.current_user_id', true)
        OR is_public = true
        OR current_setting('app.current_user_id', true) = ANY(
            SELECT jsonb_array_elements_text(access_control->'read')
        )
    );

-- 策略2: 用户只能插入自己的文档
CREATE POLICY document_insert_user ON documents
    FOR INSERT
    WITH CHECK (user_id::text = current_setting('app.current_user_id', true));

-- 策略3: 用户只能更新自己的文档
CREATE POLICY document_update_user ON documents
    FOR UPDATE
    USING (user_id::text = current_setting('app.current_user_id', true));

-- 策略4: 用户只能删除自己的文档
CREATE POLICY document_delete_user ON documents
    FOR DELETE
    USING (user_id::text = current_setting('app.current_user_id', true));

-- 策略5: 管理员可以管理所有文档
CREATE POLICY document_admin_all ON documents
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM "users" u 
            WHERE u.id::text = current_setting('app.current_user_id', true)
            AND (u.permissions->>'admin')::boolean = true
        )
    );

-- 6. 删除并重新创建安全审计表（使用正确的UUID类型）
DROP TABLE IF EXISTS security_audit CASCADE;

CREATE TABLE security_audit (
    id SERIAL PRIMARY KEY,
    user_id UUID REFERENCES "users"(id),
    action VARCHAR(50) NOT NULL,
    table_name VARCHAR(50) NOT NULL,
    record_id UUID,
    details JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. 创建审计触发器函数
CREATE OR REPLACE FUNCTION audit_security_event()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO security_audit (
        user_id, action, table_name, record_id, details,
        ip_address, user_agent
    ) VALUES (
        current_setting('app.current_user_id', true)::uuid,
        TG_OP,
        TG_TABLE_NAME,
        COALESCE(NEW.id, OLD.id),
        jsonb_build_object(
            'old', CASE WHEN TG_OP IN ('UPDATE', 'DELETE') THEN to_jsonb(OLD) ELSE NULL END,
            'new', CASE WHEN TG_OP IN ('INSERT', 'UPDATE') THEN to_jsonb(NEW) ELSE NULL END
        ),
        current_setting('app.client_ip', true)::inet,
        current_setting('app.user_agent', true)
    );
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 8. 为用户表添加审计触发器
DROP TRIGGER IF EXISTS audit_user_changes ON "users";
CREATE TRIGGER audit_user_changes
    AFTER INSERT OR UPDATE OR DELETE ON "users"
    FOR EACH ROW
    EXECUTE FUNCTION audit_security_event();

-- 9. 为文档表添加审计触发器
DROP TRIGGER IF EXISTS audit_document_changes ON documents;
CREATE TRIGGER audit_document_changes
    AFTER INSERT OR UPDATE OR DELETE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION audit_security_event();

-- 10. 创建索引以提高安全查询性能
CREATE INDEX IF NOT EXISTS idx_document_user_id ON documents(user_id);
CREATE INDEX IF NOT EXISTS idx_document_user_id_embedding ON documents(user_id, embedding);
CREATE INDEX IF NOT EXISTS idx_security_audit_user_id ON security_audit(user_id);
CREATE INDEX IF NOT EXISTS idx_security_audit_created_at ON security_audit(created_at DESC);

-- 11. 创建用于向量搜索的安全函数
CREATE OR REPLACE FUNCTION secure_vector_search(
    query_vector vector,
    user_id uuid,
    similarity_threshold float DEFAULT 0.6,
    limit_count integer DEFAULT 10
)
RETURNS TABLE (
    id uuid,
    title text,
    content text,
    similarity float,
    is_public boolean
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        d.id,
        d.title,
        d.content,
        1 - (d.embedding <=> query_vector) as similarity,
        d.is_public
    FROM documents d
    WHERE 
        -- 行级安全条件
        (d.user_id = user_id OR d.is_public = true OR user_id::text = ANY(
            SELECT jsonb_array_elements_text(d.access_control->'read')
        ))
        -- 向量相似度条件
        AND (d.embedding <=> query_vector) < similarity_threshold
        -- embedding不为空
        AND d.embedding IS NOT NULL
    ORDER BY d.embedding <=> query_vector
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 12. 创建默认管理员用户（密码需要您稍后设置）
-- 注意：这里只插入如果admin用户不存在，且您需要设置一个安全的密码哈希
INSERT INTO "users" (id, username, email, password_hash, is_active, permissions, created_at) 
SELECT 
    gen_random_uuid(),
    'admin', 
    'admin@knosphere.com',
    -- 这是一个示例哈希（admin123的bcrypt哈希），在生产环境中请更改！
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
    true,
    '{"documents": ["read", "write", "delete", "share"], "admin": true, "audit": true}'::jsonb,
    NOW()
WHERE NOT EXISTS (
    SELECT 1 FROM "users" WHERE username = 'admin'
);

-- 13. 输出配置完成信息
SELECT '✅ 安全配置完成' as message,
       count(*) as tables_secured
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('users', 'documents');