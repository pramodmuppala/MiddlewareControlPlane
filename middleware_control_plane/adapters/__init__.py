from middleware_control_plane.adapters.jboss import JBossAdapter
from middleware_control_plane.adapters.tomcat import TomcatAdapter

ADAPTERS = {
    "jboss": JBossAdapter,
    "jboss-eap": JBossAdapter,
    "tomcat": TomcatAdapter,
}


def get_adapter(name: str):
    key = name.strip().lower()
    if key not in ADAPTERS:
        raise KeyError(f"Unsupported platform adapter: {name}")
    return ADAPTERS[key]()
