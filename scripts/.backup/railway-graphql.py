#!/usr/bin/env python3
"""
Railway GraphQL API client for template management.

Supports:
  - Querying templates and their serializedConfig
  - Updating template variables via serializedConfig + templateDeployV2
  - Publishing templates

Usage:
    python3 railway-graphql.py query <template_id>
    python3 railway-graphql.py update-vars <template_id> <vars_json_file>
    python3 railway-graphql.py deploy <template_id> <project_id>
    python3 railway-graphql.py publish <template_id> <category> <description> <readme_path>
"""

import json, os, sys, urllib.request

TOKEN = open(os.path.expanduser("~/.railway/api-token")).read().strip()
ENDPOINT = "https://backboard.railway.com/graphql/v2"


def gql(query, variables=None):
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": "Bearer " + TOKEN,
            "Content-Type": "application/json",
            "User-Agent": "railway-cli/5.23.1",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"HTTP {e.code}: {body[:500]}", file=sys.stderr)
        return None


def query_template(template_id):
    """Query a template's full config including serializedConfig."""
    q = """{
        template(id: "%s") {
            id name code status serializedConfig
            services { edges { node { id config } } }
        }
    }""" % template_id
    r = gql(q)
    if not r or "errors" in r:
        print(f"Query failed: {r}", file=sys.stderr)
        return None
    return r["data"]["template"]


def get_workspace_id():
    """Get the first workspace ID."""
    r = gql("{ me { workspaces { id name } } }")
    if r and r["data"]["me"]["workspaces"]:
        return r["data"]["me"]["workspaces"][0]["id"]
    return None


def update_serialized_config(template_id, vars_manifest):
    """
    Read the current serializedConfig, merge in variable definitions,
    and deploy the updated config.
    
    vars_manifest format: {"VARIABLE_NAME": {"defaultValue": "...", "description": "...", "isOptional": false}, ...}
    """
    # Step 1: Read current template
    tmpl = query_template(template_id)
    if not tmpl:
        print("Template not found", file=sys.stderr)
        return None

    # Step 2: Parse serializedConfig
    sc = tmpl.get("serializedConfig") or {}
    if isinstance(sc, str):
        sc = json.loads(sc)
    if not isinstance(sc, dict) or "services" not in sc:
        sc = {"services": {}}

    # Step 3: Inject variables into each service's config
    services = sc.get("services", {})
    for svc_id, svc_cfg in services.items():
        if "variables" not in svc_cfg:
            svc_cfg["variables"] = {}
        for var_name, var_def in vars_manifest.items():
            svc_cfg["variables"][var_name] = var_def

    # Step 4: Deploy with updated config
    ws_id = get_workspace_id()
    deploy_input = {
        "templateId": template_id,
        "serializedConfig": sc,
    }
    if ws_id:
        deploy_input["workspaceId"] = ws_id

    q = """
    mutation DeployTemplate($input: TemplateDeployV2Input!) {
        templateDeployV2(input: $input) {
            projectId
            workflowId
        }
    }
    """
    r = gql(q, {"input": deploy_input})
    if r and "data" in r:
        print(json.dumps(r["data"], indent=2))
        return r["data"]["templateDeployV2"]
    else:
        print(f"Deploy failed: {r}", file=sys.stderr)
        return None


def publish_template(template_id, category, description, readme_path, image=None):
    """Publish a template."""
    with open(readme_path) as f:
        readme = f.read()

    q = """
    mutation PublishTemplate($id: String!, $input: TemplatePublishInput!) {
        templatePublish(id: $id, input: $input) {
            id code name status
        }
    }
    """
    pub_input = {
        "category": category,
        "description": description,
        "readme": readme,
    }
    if image:
        pub_input["image"] = image

    r = gql(q, {"id": template_id, "input": pub_input})
    if r and "data" in r:
        print(json.dumps(r["data"], indent=2))
        return r["data"]["templatePublish"]
    else:
        print(f"Publish failed: {r}", file=sys.stderr)
        return None


def list_templates():
    """List all templates in the workspace."""
    ws_id = get_workspace_id()
    if not ws_id:
        print("No workspace found", file=sys.stderr)
        return

    q = """{
        workspaceTemplates(workspaceId: "%s") {
            edges { node { id name code status } }
        }
    }""" % ws_id
    r = gql(q)
    if r:
        edges = r["data"]["workspaceTemplates"]["edges"]
        for e in edges:
            n = e["node"]
            print(f'{n["code"]:30s} {n["status"]:12s} {n["id"]} {n["name"]}')


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "list":
        list_templates()
    elif cmd == "query" and len(sys.argv) >= 3:
        result = query_template(sys.argv[2])
        if result:
            print(json.dumps(result, indent=2, default=str))
    elif cmd == "update-vars" and len(sys.argv) >= 4:
        vars_file = sys.argv[3]
        with open(vars_file) as f:
            vars_manifest = json.load(f)
        result = update_serialized_config(sys.argv[2], vars_manifest)
    elif cmd == "deploy" and len(sys.argv) >= 4:
        # Deploy with current config (no variable changes)
        ws_id = get_workspace_id()
        tmpl = query_template(sys.argv[2])
        if tmpl:
            sc = tmpl.get("serializedConfig", "{}")
            if isinstance(sc, str):
                sc = json.loads(sc)
            deploy_input = {
                "templateId": sys.argv[2],
                "serializedConfig": sc,
            }
            if ws_id:
                deploy_input["workspaceId"] = ws_id
            q = """
            mutation DeployTemplate($input: TemplateDeployV2Input!) {
                templateDeployV2(input: $input) {
                    projectId
                    workflowId
                }
            }
            """
            r = gql(q, {"input": deploy_input})
            print(json.dumps(r, indent=2) if r else "Failed")
    elif cmd == "publish" and len(sys.argv) >= 6:
        image = sys.argv[6] if len(sys.argv) > 6 else None
        result = publish_template(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], image)
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
