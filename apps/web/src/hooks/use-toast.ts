"use client";

import { toast as sonnerToast } from "sonner";

type ToastProps = {
  title?: string;
  description?: string;
  action?: React.ReactNode;
  variant?: "default" | "destructive";
  id?: string;
};

// 主 toast 函数
export const toast = (props: ToastProps) => {
  const { title, description, variant, action, id } = props;
  
  if (variant === "destructive") {
    return sonnerToast.error(title, {
      description,
      id,
      duration: 5000,
    });
  }
  
  return sonnerToast(title, {
    description,
    action,
    id,
    duration: 5000,
  });
};

// 添加 dismiss 方法
toast.dismiss = (toastId?: string) => {
  sonnerToast.dismiss(toastId);
};

// 添加 error 快捷方法
toast.error = (props: Omit<ToastProps, "variant">) => {
  return toast({ ...props, variant: "destructive" });
};

// 添加 success 方法
toast.success = (props: Omit<ToastProps, "variant">) => {
  return sonnerToast.success(props.title, {
    description: props.description,
    id: props.id,
    duration: 5000,
  });
};

// 添加 info 方法
toast.info = (props: Omit<ToastProps, "variant">) => {
  return sonnerToast.info(props.title, {
    description: props.description,
    id: props.id,
    duration: 5000,
  });
};

// 添加 warning 方法
toast.warning = (props: Omit<ToastProps, "variant">) => {
  return sonnerToast.warning(props.title, {
    description: props.description,
    id: props.id,
    duration: 5000,
  });
};

// 添加 message 方法 (无图标)
toast.message = (props: Omit<ToastProps, "variant">) => {
  return sonnerToast.message(props.title, {
    description: props.description,
    id: props.id,
    duration: 5000,
  });
};

// 添加 promise 方法
toast.promise = sonnerToast.promise;

// 自定义 useToast hook，保持向后兼容
export const useToast = () => {
  return {
    toast,
    dismiss: toast.dismiss,
    // 为了兼容性，返回一个空数组（原代码中可能使用了 toasts 状态）
    toasts: [],
  };
};