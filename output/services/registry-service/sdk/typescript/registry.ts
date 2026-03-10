// Generated TypeScript types from registry.proto
// This is a simplified generator. Use ts-proto for production.

export interface HealthCheckConfig {
  http_endpoint: string;
  grpc_service: string;
  tcp_address: string;
  interval_seconds: number;
  timeout_seconds: number;
  deregister_after_seconds: number;
}

export interface ProvidesConfig {
  events: string[];
}

export interface RegisterRequest {
  name: string;
  version: string;
  instance_id: string;
  address: string;
  port: number;
  protocol: string;
  depends: string[];
  health_check: HealthCheckConfig;
  tags: string[];
  provides: ProvidesConfig;
}

export interface RegisterResponse {
  instance_id: string;
  consul_service_id: string;
  registered_at: string;
  health_check_id: string;
}

export interface DeregisterRequest {
  instance_id: string;
  service_name: string;
  version: string;
  reason: string;
}

export interface DeregisterResponse {
  success: boolean;
  deregistered_at: string;
}

export interface HeartbeatRequest {
  instance_id: string;
  status: string;
}

export interface HeartbeatResponse {
  instance_id: string;
  status: string;
  last_heartbeat: string;
}

export interface ServiceInstance {
  instance_id: string;
  address: string;
  port: number;
  protocol: string;
  version: string;
  health_status: string;
  tags: string[];
}

export interface DiscoverRequest {
  service_name: string;
  version_constraint: string;
  tags: string[];
  healthy_only: boolean;
}

export interface DiscoverResponse {
  service: string;
  instances: ServiceInstance[];
  total_instances: number;
  healthy_instances: number;
}

export interface WatchRequest {
  service_name: string;
}

export interface ServiceEvent {
  event_type: string;
  service_name: string;
  instance_id: string;
  version: string;
  instance: ServiceInstance;
  timestamp: string;
}

export interface ListServicesRequest {
  tags: string[];
}

export interface ServiceSummary {
  name: string;
  versions: string[];
  instance_count: number;
  healthy_count: number;
  tags: string[];
}

export interface ListServicesResponse {
  services: ServiceSummary[];
  total_services: number;
}

export interface InstanceHealthCount {
  healthy: number;
  warning: number;
  critical: number;
}

export interface ServiceHealthSummary {
  name: string;
  status: string;
  instances: InstanceHealthCount;
}

export interface GetHealthResponse {
  services: ServiceHealthSummary[];
  overall_status: string;
  total_instances: number;
  healthy_instances: number;
}

export interface GetServiceHealthRequest {
  service_name: string;
}

export interface HealthCheck {
  name: string;
  status: string;
  output: string;
  last_check: string;
}

export interface InstanceHealthDetail {
  instance_id: string;
  status: string;
  checks: HealthCheck[];
  uptime_seconds: number;
}

export interface GetServiceHealthResponse {
  service: string;
  status: string;
  instances: InstanceHealthDetail[];
}
