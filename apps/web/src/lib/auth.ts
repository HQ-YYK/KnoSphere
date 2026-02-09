/**
 * KnoSphere 前端认证服务
 * 处理登录、令牌管理、权限验证
 */

// 用户接口
export interface User {
  id: string;
  username: string;
  email: string;
  is_active: boolean;
  permissions: Record<string, any>;
  created_at: string;
  last_login?: string;
}

// 登录响应接口
export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user_id: string;
  username: string;
  permissions: Record<string, any>;
}

// 登录请求接口
export interface LoginRequest {
  username: string;
  password: string;
}

// 注册请求接口
export interface RegisterRequest {
  username: string;
  email: string;
  password: string;
}

// 密码修改接口
export interface PasswordChangeRequest {
  current_password: string;
  new_password: string;
}

class AuthService {
  private static instance: AuthService;
  private tokenKey = 'knosphere_token';
  private userKey = 'knosphere_user';
  
  private constructor() {}
  
  public static getInstance(): AuthService {
    if (!AuthService.instance) {
      AuthService.instance = new AuthService();
    }
    return AuthService.instance;
  }
  
  // 获取当前令牌
  public getToken(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem(this.tokenKey);
  }
  
  // 设置令牌
  public setToken(token: string): void {
    if (typeof window === 'undefined') return;
    localStorage.setItem(this.tokenKey, token);
  }
  
  // 移除令牌
  public removeToken(): void {
    if (typeof window === 'undefined') return;
    localStorage.removeItem(this.tokenKey);
  }
  
  // 获取当前用户
  public getUser(): User | null {
    if (typeof window === 'undefined') return null;
    const userStr = localStorage.getItem(this.userKey);
    return userStr ? JSON.parse(userStr) : null;
  }
  
  // 设置用户
  public setUser(user: User): void {
    if (typeof window === 'undefined') return;
    localStorage.setItem(this.userKey, JSON.stringify(user));
  }
  
  // 移除用户
  public removeUser(): void {
    if (typeof window === 'undefined') return;
    localStorage.removeItem(this.userKey);
  }
  
  // 检查是否已登录
  public isAuthenticated(): boolean {
    return !!this.getToken();
  }
  
  // 检查用户权限
  public hasPermission(resource: string, action: string): boolean {
    const user = this.getUser();
    if (!user) return false;
    
    // 管理员拥有所有权限
    if (user.permissions?.admin === true) {
      return true;
    }
    
    // 检查特定资源权限
    const resourcePerms = user.permissions?.[resource];
    if (Array.isArray(resourcePerms)) {
      return resourcePerms.includes(action);
    }
    
    return false;
  }
  
  // 登录
  public async login(credentials: LoginRequest): Promise<LoginResponse> {
    const response = await fetch('http://localhost:8000/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(credentials),
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || '登录失败');
    }
    
    const data: LoginResponse = await response.json();
    
    // 存储令牌
    this.setToken(data.access_token);
    
    // 存储用户信息
    this.setUser({
      id: data.user_id,
      username: data.username,
      email: '',
      is_active: true,
      permissions: data.permissions,
      created_at: new Date().toISOString(),
    });
    
    return data;
  }
  
  // 注册
  public async register(userData: RegisterRequest): Promise<User> {
    const response = await fetch('http://localhost:8000/auth/register', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(userData),
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || '注册失败');
    }
    
    return await response.json();
  }
  
  // 注销
  public logout(): void {
    this.removeToken();
    this.removeUser();
    
    // 重定向到登录页
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
  }
  
  // 获取当前用户信息
  public async getCurrentUser(): Promise<User | null> {
    const token = this.getToken();
    if (!token) return null;
    
    try {
      const response = await fetch('http://localhost:8000/auth/me', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (response.ok) {
        const user: User = await response.json();
        this.setUser(user);
        return user;
      }
    } catch (error) {
      console.error('获取用户信息失败:', error);
    }
    
    return null;
  }
  
  // 修改密码
  public async changePassword(passwordData: PasswordChangeRequest): Promise<void> {
    const token = this.getToken();
    if (!token) throw new Error('未登录');
    
    const response = await fetch('http://localhost:8000/auth/change-password', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(passwordData),
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || '修改密码失败');
    }
  }
  
  // 刷新令牌
  public async refreshToken(): Promise<LoginResponse | null> {
    const token = this.getToken();
    if (!token) return null;
    
    try {
      const response = await fetch('http://localhost:8000/auth/refresh', {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      
      if (response.ok) {
        const data: LoginResponse = await response.json();
        this.setToken(data.access_token);
        return data;
      }
    } catch (error) {
      console.error('刷新令牌失败:', error);
    }
    
    return null;
  }
  
  // 创建安全的 fetch 请求
  public async secureFetch(url: string, options: RequestInit = {}): Promise<Response> {
    const token = this.getToken();
    
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      ...options.headers,
    };
    
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(url, {
      ...options,
      headers,
    });
    
    // 处理 401 未授权
    if (response.status === 401) {
      // 尝试刷新令牌
      const refreshed = await this.refreshToken();
      if (refreshed) {
        // 重试原始请求
        return this.secureFetch(url, options);
      } else {
        // 刷新失败，注销用户
        this.logout();
        throw new Error('会话已过期，请重新登录');
      }
    }
    
    return response;
  }
  
  // 初始化认证状态
  public async initialize(): Promise<User | null> {
    if (this.isAuthenticated()) {
      return this.getCurrentUser();
    }
    return null;
  }
}

export default AuthService.getInstance();