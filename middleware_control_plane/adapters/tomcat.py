from middleware_control_plane.adapters.base import MiddlewareAdapter


class TomcatAdapter(MiddlewareAdapter):
    platform_name = "tomcat"
    extra_vars_key = "tomcat"

    def describe(self) -> str:
        return "Tomcat adapter using shared CATALINA_HOME and per-instance CATALINA_BASE directories"
