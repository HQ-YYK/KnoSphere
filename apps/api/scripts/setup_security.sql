-- KnoSphere 企业级安全配置脚本
-- 行级安全 (RLS) 配置

-- 1. 为用户表添加额外安全字段
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS last_login TIMESTAMP;
ALTER TABLE "user" ADD COLUMN IF NOT EXISTS permissions JSONB DEFAULT '{"documents": ["read", "write", "delete"], "admin": false}'::jsonb;

-- 2. 为文档表添加安全字段
ALTER TABLE document ADD COLUMN IF NOT EXISTS is_public BOOLEAN DEFAULT false;
ALTER TABLE document ADD COLUMN IF NOT EXISTS tags TEXT[] DEFAULT '{}';
ALTER TABLE document ADD COLUMN IF NOT EXISTS access_control JSONB DEFAULT '{"read": [], "write": [], "delete": []}'::jsonb;

-- 3. 启用行级安全
ALTER TABLE "user" ENABLE ROW LEVEL SECURITY;
ALTER TABLE document ENABLE ROW LEVEL SECURITY;

-- 4. 为用户表创建安全策略
-- 策略1: 用户只能查看自己的信息
CREATE POLICY user_select_own ON "user"
    FOR SELECT
    USING (id = current_setting('app.current_user_id', true)::integer);

-- 策略2: 用户只能更新自己的信息
CREATE POLICY user_update_own ON "user"
    FOR UPDATE
    USING (id = current_setting('app.current_user_id', true)::integer);

-- 策略3: 管理员可以查看所有用户
CREATE POLICY user_select_admin ON "user"
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM "user" u 
            WHERE u.id = current_setting('app.current_user_id', true)::integer 
            AND u.permissions->>'admin' = 'true'
        )
    );

-- 5. 为文档表创建安全策略
-- 策略1: 用户可以查看自己的文档和公开文档
CREATE POLICY document_select_user ON document
    FOR SELECT
    USING (
        user_id = current_setting('app.current_user_id', true)::integer 
        OR is_public = true
        OR current_setting('app.current_user_id', true)::integer = ANY(
            SELECT jsonb_array_elements_text(access_control->'read')::integer
        )
    );

-- 策略2: 用户只能插入自己的文档
CREATE POLICY document_insert_user ON document
    FOR INSERT
    WITH CHECK (user_id = current_setting('app.current_user_id', true)::integer);

-- 策略3: 用户只能更新自己的文档
CREATE POLICY document_update_user ON document
    FOR UPDATE
    USING (user_id = current_setting('app.current_user_id', true)::integer);

-- 策略4: 用户只能删除自己的文档
CREATE POLICY document_delete_user ON document
    FOR DELETE
    USING (user_id = current_setting('app.current_user_id', true)::integer);

-- 策略5: 管理员可以管理所有文档
CREATE POLICY document_admin_all ON document
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM "user" u 
            WHERE u.id = current_setting('app.current_user_id', true)::integer 
            AND u.permissions->>'admin' = 'true'
        )
    );

-- 6. 创建安全审计表
CREATE TABLE IF NOT EXISTS security_audit (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES "user"(id),
    action VARCHAR(50) NOT NULL,
    table_name VARCHAR(50) NOT NULL,
    record_id INTEGER,
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
        current_setting('app.current_user_id', true)::integer,
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
DROP TRIGGER IF EXISTS audit_user_changes ON "user";
CREATE TRIGGER audit_user_changes
    AFTER INSERT OR UPDATE OR DELETE ON "user"
    FOR EACH ROW
    EXECUTE FUNCTION audit_security_event();

-- 9. 为文档表添加审计触发器
DROP TRIGGER IF EXISTS audit_document_changes ON document;
CREATE TRIGGER audit_document_changes
    AFTER INSERT OR UPDATE OR DELETE ON document
    FOR EACH ROW
    EXECUTE FUNCTION audit_security_event();

-- 10. 创建索引以提高安全查询性能
CREATE INDEX IF NOT EXISTS idx_document_user_id ON document(user_id);
CREATE INDEX IF NOT EXISTS idx_document_user_id_embedding ON document(user_id, embedding);
CREATE INDEX IF NOT EXISTS idx_security_audit_user_id ON security_audit(user_id);
CREATE INDEX IF NOT EXISTS idx_security_audit_created_at ON security_audit(created_at DESC);

-- 11. 创建用于向量搜索的安全函数
CREATE OR REPLACE FUNCTION secure_vector_search(
    query_vector vector,
    user_id integer,
    similarity_threshold float DEFAULT 0.6,
    limit_count integer DEFAULT 10
)
RETURNS TABLE (
    id integer,
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
    FROM document d
    WHERE 
        -- 行级安全条件
        (d.user_id = user_id OR d.is_public = true OR user_id = ANY(
            SELECT jsonb_array_elements_text(d.access_control->'read')::integer
        ))
        -- 向量相似度条件
        AND (d.embedding <=> query_vector) < similarity_threshold
    ORDER BY d.embedding <=> query_vector
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 12. 创建默认管理员用户（密码：admin123）
INSERT INTO "user" (username, email, permissions, created_at) 
VALUES (
    'admin', 
    'admin@knosphere.com',
    '{"documents": ["read", "write", "delete", "share"], "admin": true, "audit": true}'::jsonb,
    NOW()  -- 或者 CURRENT_TIMESTAMP
)
ON CONFLICT (username) DO UPDATE SET 
    permissions = EXCLUDED.permissions;

-- 13. 输出配置完成信息
SELECT '✅ 安全配置完成' as message,
       count(*) as tables_secured
FROM pg_tables 
WHERE schemaname = 'public' 
AND tablename IN ('user', 'document');