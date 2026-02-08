"use client";

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { LogIn, UserPlus, Key, User } from 'lucide-react';

export default function LoginPage() {
  const router = useRouter();
  const { login, isLoading } = useAuth();
  
  const [formData, setFormData] = useState({
    username: '',
    password: '',
  });
  const [error, setError] = useState('');
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [registerData, setRegisterData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
  });

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    try {
      await login(formData);
      router.push('/');
    } catch (err: any) {
      setError(err.message || '登录失败');
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (registerData.password !== registerData.confirmPassword) {
      setError('两次输入的密码不一致');
      return;
    }

    if (registerData.password.length < 6) {
      setError('密码长度至少为6位');
      return;
    }

    try {
      const { login } = useAuth();
      await login({
        username: registerData.username,
        password: registerData.password,
      });
      router.push('/');
    } catch (err: any) {
      setError(err.message || '注册失败');
    }
  };

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-400 via-emerald-400 to-cyan-400 bg-clip-text text-transparent">
            KnoSphere
          </h1>
          <p className="text-zinc-400 mt-2">企业级智能知识库系统</p>
        </div>

        {/* 模式切换 */}
        <div className="flex mb-6 bg-zinc-900/50 rounded-lg p-1">
          <button
            onClick={() => setIsRegisterMode(false)}
            className={`flex-1 py-2 rounded-md text-sm font-medium transition-colors ${
              !isRegisterMode
                ? 'bg-blue-600 text-white'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <div className="flex items-center justify-center gap-2">
              <LogIn className="w-4 h-4" />
              登录
            </div>
          </button>
          <button
            onClick={() => setIsRegisterMode(true)}
            className={`flex-1 py-2 rounded-md text-sm font-medium transition-colors ${
              isRegisterMode
                ? 'bg-emerald-600 text-white'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            <div className="flex items-center justify-center gap-2">
              <UserPlus className="w-4 h-4" />
              注册
            </div>
          </button>
        </div>

        {/* 错误提示 */}
        {error && (
          <Alert variant="destructive" className="mb-6">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* 登录表单 */}
        {!isRegisterMode ? (
          <Card className="bg-zinc-900/30 border-zinc-800 backdrop-blur-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Key className="w-5 h-5 text-blue-400" />
                用户登录
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleLogin} className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-zinc-300">
                    用户名
                  </label>
                  <div className="relative">
                    <User className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-zinc-500" />
                    <Input
                      type="text"
                      placeholder="请输入用户名"
                      className="pl-10 bg-zinc-800 border-zinc-700"
                      value={formData.username}
                      onChange={(e) =>
                        setFormData({ ...formData, username: e.target.value })
                      }
                      required
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-zinc-300">
                    密码
                  </label>
                  <div className="relative">
                    <Key className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-zinc-500" />
                    <Input
                      type="password"
                      placeholder="请输入密码"
                      className="pl-10 bg-zinc-800 border-zinc-700"
                      value={formData.password}
                      onChange={(e) =>
                        setFormData({ ...formData, password: e.target.value })
                      }
                      required
                    />
                  </div>
                </div>

                <Button
                  type="submit"
                  className="w-full bg-gradient-to-r from-blue-600 to-emerald-600 hover:from-blue-700 hover:to-emerald-700"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                      登录中...
                    </>
                  ) : (
                    '登录'
                  )}
                </Button>
              </form>
            </CardContent>
            <CardFooter className="flex flex-col gap-3 border-t border-zinc-800 pt-6">
              <div className="text-center text-sm text-zinc-500">
                测试账户: <code className="bg-zinc-800 px-2 py-1 rounded">admin</code> / 
                <code className="bg-zinc-800 px-2 py-1 rounded ml-2">admin123</code>
              </div>
              <Button
                variant="outline"
                className="w-full border-zinc-700 text-zinc-400 hover:text-zinc-200"
                onClick={() => {
                  setFormData({
                    username: 'admin',
                    password: 'admin123',
                  });
                }}
              >
                使用测试账户
              </Button>
            </CardFooter>
          </Card>
        ) : (
          /* 注册表单 */
          <Card className="bg-zinc-900/30 border-zinc-800 backdrop-blur-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <UserPlus className="w-5 h-5 text-emerald-400" />
                用户注册
              </CardTitle>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleRegister} className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium text-zinc-300">
                    用户名
                  </label>
                  <Input
                    type="text"
                    placeholder="请输入用户名"
                    className="bg-zinc-800 border-zinc-700"
                    value={registerData.username}
                    onChange={(e) =>
                      setRegisterData({
                        ...registerData,
                        username: e.target.value,
                      })
                    }
                    required
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-zinc-300">
                    邮箱
                  </label>
                  <Input
                    type="email"
                    placeholder="请输入邮箱"
                    className="bg-zinc-800 border-zinc-700"
                    value={registerData.email}
                    onChange={(e) =>
                      setRegisterData({
                        ...registerData,
                        email: e.target.value,
                      })
                    }
                    required
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-zinc-300">
                    密码
                  </label>
                  <Input
                    type="password"
                    placeholder="请输入密码（至少6位）"
                    className="bg-zinc-800 border-zinc-700"
                    value={registerData.password}
                    onChange={(e) =>
                      setRegisterData({
                        ...registerData,
                        password: e.target.value,
                      })
                    }
                    required
                  />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium text-zinc-300">
                    确认密码
                  </label>
                  <Input
                    type="password"
                    placeholder="请再次输入密码"
                    className="bg-zinc-800 border-zinc-700"
                    value={registerData.confirmPassword}
                    onChange={(e) =>
                      setRegisterData({
                        ...registerData,
                        confirmPassword: e.target.value,
                      })
                    }
                    required
                  />
                </div>

                <Button
                  type="submit"
                  className="w-full bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-700 hover:to-teal-700"
                  disabled={isLoading}
                >
                  {isLoading ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                      注册中...
                    </>
                  ) : (
                    '注册'
                  )}
                </Button>
              </form>
            </CardContent>
            <CardFooter className="border-t border-zinc-800 pt-6">
              <p className="text-center text-sm text-zinc-500 w-full">
                已有账户？{' '}
                <button
                  onClick={() => setIsRegisterMode(false)}
                  className="text-blue-400 hover:text-blue-300 underline"
                >
                  立即登录
                </button>
              </p>
            </CardFooter>
          </Card>
        )}

        {/* 返回首页 */}
        <div className="mt-8 text-center">
          <Link
            href="/"
            className="text-sm text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            ← 返回首页
          </Link>
        </div>

        {/* 安全提示 */}
        <div className="mt-8 text-center">
          <p className="text-xs text-zinc-600">
            🔒 所有数据均经过加密传输和存储
            <br />
            📚 您的知识文档将安全隔离，仅您可见
          </p>
        </div>
      </div>
    </div>
  );
}