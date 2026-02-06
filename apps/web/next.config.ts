/** @type {import('next').NextConfig} */

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // 开启 React 19 自动编译器，不再需要手动写 useMemo
  reactCompiler: true, 
  // 开启部分预渲染 (Partial Pre-rendering)，实现秒级首屏加载
  cacheComponents: true, 
};

export default nextConfig;
