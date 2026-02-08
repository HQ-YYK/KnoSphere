"use client";

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import AuthService, { User, LoginRequest, RegisterRequest } from '@/lib/auth';

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: LoginRequest) => Promise<void>;
  register: (userData: RegisterRequest) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  hasPermission: (resource: string, action: string) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    initializeAuth();
  }, []);

  const initializeAuth = async () => {
    setIsLoading(true);
    try {
      const currentUser = await AuthService.getCurrentUser();
      setUser(currentUser);
    } catch (error) {
      console.error('认证初始化失败:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (credentials: LoginRequest) => {
    setIsLoading(true);
    try {
      await AuthService.login(credentials);
      const currentUser = await AuthService.getCurrentUser();
      setUser(currentUser);
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (userData: RegisterRequest) => {
    setIsLoading(true);
    try {
      await AuthService.register(userData);
      // 注册后自动登录
      await login({
        username: userData.username,
        password: userData.password,
      });
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    AuthService.logout();
    setUser(null);
  };

  const refreshUser = async () => {
    const currentUser = await AuthService.getCurrentUser();
    setUser(currentUser);
  };

  const hasPermission = (resource: string, action: string): boolean => {
    return AuthService.hasPermission(resource, action);
  };

  const value: AuthContextType = {
    user,
    isLoading,
    isAuthenticated: !!user,
    login,
    register,
    logout,
    refreshUser,
    hasPermission,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

// 保护路由的高阶组件
export function withAuth<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  requiredPermissions?: { resource: string; action: string }[]
) {
  return function WithAuthComponent(props: P) {
    const { user, isLoading, hasPermission } = useAuth();

    useEffect(() => {
      if (!isLoading && !user) {
        // 未登录，重定向到登录页
        window.location.href = '/login';
      }
    }, [user, isLoading]);

    if (isLoading) {
      return (
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
            <p className="text-zinc-400">加载中...</p>
          </div>
        </div>
      );
    }

    if (!user) {
      return null; // 重定向中
    }

    // 检查权限
    if (requiredPermissions) {
      const hasAllPermissions = requiredPermissions.every(({ resource, action }) =>
        hasPermission(resource, action)
      );

      if (!hasAllPermissions) {
        return (
          <div className="flex items-center justify-center min-h-screen">
            <div className="text-center p-8 bg-zinc-900/50 rounded-lg border border-zinc-800">
              <div className="text-red-500 text-4xl mb-4">🚫</div>
              <h2 className="text-xl font-bold text-zinc-100 mb-2">权限不足</h2>
              <p className="text-zinc-400 mb-4">
                您没有访问此页面的权限
              </p>
              <button
                onClick={() => window.history.back()}
                className="px-4 py-2 bg-zinc-800 hover:bg-zinc-700 rounded-lg text-zinc-200"
              >
                返回
              </button>
            </div>
          </div>
        );
      }
    }

    return <WrappedComponent {...props} />;
  };
}