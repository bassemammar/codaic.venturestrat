-- tenant-header plugin handler
-- Extracts tenant_id and user_id (sub) from JWT claims and adds
-- X-Tenant-ID and X-User-ID headers for downstream services

local TenantHeaderHandler = {
    PRIORITY = 900,  -- After auth (JWT plugin), before routing
    VERSION = "1.0.0",
}

function TenantHeaderHandler:access(conf)
    -- Get tenant_id from JWT claims (set by JWT plugin)
    local jwt_claims = kong.ctx.shared.jwt_claims

    if jwt_claims and jwt_claims.tenant_id then
        -- Set header for downstream services
        kong.service.request.set_header("X-Tenant-ID", jwt_claims.tenant_id)

        -- Also set for logging and metrics
        kong.ctx.plugin.tenant_id = jwt_claims.tenant_id

        -- Extract user identity from JWT sub claim (optional — no 401 if missing)
        if jwt_claims.sub then
            kong.service.request.set_header("X-User-ID", jwt_claims.sub)
            kong.ctx.plugin.user_id = jwt_claims.sub
        end

        -- Add tenant context to logs
        kong.log.debug("Tenant context set: ", jwt_claims.tenant_id)
    else
        -- No tenant in token - check if path is excluded
        local path = kong.request.get_path()
        local exclude_paths = conf.exclude_paths or {}

        for _, pattern in ipairs(exclude_paths) do
            if string.match(path, pattern) then
                kong.log.debug("Path excluded from tenant requirement: ", path)
                return
            end
        end

        -- Path not excluded and no tenant - reject request
        kong.log.warn("Missing tenant_id in JWT claims for path: ", path)
        return kong.response.exit(401, {
            error = "missing_tenant",
            message = "Token must contain tenant_id claim"
        })
    end
end

-- Add tenant_id to response headers for debugging (optional)
function TenantHeaderHandler:header_filter(conf)
    if conf.debug_header and kong.ctx.plugin.tenant_id then
        kong.response.set_header("X-Debug-Tenant-ID", kong.ctx.plugin.tenant_id)
    end
end

-- Add tenant_id to logs for audit purposes
function TenantHeaderHandler:log(conf)
    local tenant_id = kong.ctx.plugin.tenant_id
    local user_id = kong.ctx.plugin.user_id
    if tenant_id then
        -- Add tenant and user context to structured logs
        kong.log.set_serialize_value("tenant_id", tenant_id)
        if user_id then
            kong.log.set_serialize_value("user_id", user_id)
        end

        -- Emit custom metrics if enabled
        if conf.emit_metrics then
            local counter_name = "tenant_requests"
            kong.log.inspect({
                metric = counter_name,
                tenant_id = tenant_id,
                service = kong.router.get_service().name or "unknown",
                route = (kong.router.get_route() or {}).name or "unknown"
            })
        end
    end
end

return TenantHeaderHandler
