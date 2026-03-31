from middleware_control_plane.adapters.base import MiddlewareAdapter


class JBossAdapter(MiddlewareAdapter):
    platform_name = "jboss"
    extra_vars_key = "jboss"

    def describe(self) -> str:
        return "JBoss EAP adapter using shared product home and per-instance runtime directories"
