# Auto Increase / Decrease Tomcat 10

Ansible-based automation to create, configure, start, and optionally remove multiple Tomcat 10 instances on a single host.

This project uses:

- **shared `CATALINA_HOME`** for the Tomcat installation
- **per-instance `CATALINA_BASE`** directories under `/opt/tomcat`
- generated per-instance `server.xml`
- per-instance `setenv.sh`
- optional cleanup of extra instances when scaling down

## How it works

The playbook:

1. reads the base Tomcat configuration from `vars/main.yml`
2. discovers existing instance directories under `catalina_base_root`
3. computes which instances are:
   - already present
   - missing
   - extra
4. creates **only missing instances**
5. leaves existing instances **untouched**
6. optionally destroys extra instances if `destroy_enabled=true`

### Current behavior

- If `app1` already exists and you request `instance_count=5`, it creates:
  - `app2`
  - `app3`
  - `app4`
  - `app5`

It does **not** restart or redeploy `app1`.

- If you reduce the requested instance count and set `destroy_enabled=true`, extra instances are stopped and removed.

## Directory layout

```text
/opt/products/tomcat/tomcat10        # shared Tomcat installation (CATALINA_HOME)
/opt/tomcat/app1                     # instance base (CATALINA_BASE)
├── bin
│   └── setenv.sh
├── conf
│   └── server.xml
├── logs
├── temp
├── webapps
└── work
```

## Notes

This vendored copy is integrated into the umbrella monorepo under `platforms/tomcat/`.
It preserves the original top-level playbook, autoscaler, vars, tasks, and role structure so the middleware control plane can call it locally from one repository root.
