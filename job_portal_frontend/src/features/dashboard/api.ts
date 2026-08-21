import { authApiRequest } from "@/lib/api-client";
import type {
  AdminDashboardDto,
  EmployerDashboardDto,
} from "@/features/dashboard/types";

export const getEmployerDashboard = () => authApiRequest<EmployerDashboardDto>("/api/dashboard/");
export const getAdminDashboard = () => authApiRequest<AdminDashboardDto>("/api/dashboard/");
