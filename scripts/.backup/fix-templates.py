#!/usr/bin/env python3
"""
Fix published Railway templates:
1. Fix broken deploy-on-railway links in READMEs (wrong domain, wrong codes)
2. Set OG images on published templates that lack them
"""
import importlib.util, json, os, sys, re

BASE = "/var/home/ihshim523/Work/railway"

# Load railway-graphql module
spec = importlib.util.spec_from_file_location("rgql", f"{BASE}/scripts/railway-graphql.py")
rgql = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rgql)

# Published templates from the API, mapped by their directory name
# Format: {directory_name: {code, repo, needs_og_image, current_deploy_link, current_og_image}}
TEMPLATES = {
    "railway-arcane":       {"code": "BV1O-V",        "status": "UNPUBLISHED", "repo": "railway-arcane"},
    "railway-beszel":       {"code": "beszel",         "status": "PUBLISHED",   "repo": "railway-beszel"},
    "railway-blinko":       {"code": "blinko",         "status": "PUBLISHED",   "repo": "railway-blinko"},
    "railway-blocky":       {"code": "blocky",         "status": "PUBLISHED",   "repo": "railway-blocky"},
    "railway-changedetection.io": {"code": "changedetectionio-1", "status": "PUBLISHED", "repo": "railway-changedetection.io"},
    "railway-dragonfly":    {"code": "dragonfly-1",         "status": "PUBLISHED",   "repo": "railway-dragonfly"},
    "railway-filebrowser":  {"code": "filebrowser",    "status": "PUBLISHED",   "repo": "railway-filebrowser"},
    "railway-ghost":        {"code": "railway-ghost",  "status": "PUBLISHED",   "repo": "railway-ghost"},
    "railway-gotify":       {"code": "gotify",          "status": "PUBLISHED",  "repo": "railway-gotify"},
    "railway-homepage":     {"code": "homepage",       "status": "PUBLISHED",   "repo": "railway-homepage"},
    "railway-hoppscotch":   {"code": "railway-hoppscotch", "status": "PUBLISHED", "repo": "railway-hoppscotch"},
    "railway-kanboard":     {"code": "kanboard-2",     "status": "PUBLISHED",   "repo": "railway-kanboard"},
    "railway-memos":        {"code": "memos-3",        "status": "PUBLISHED",   "repo": "railway-memos"},
    "railway-n8n":          {"code": "railway-n8n",    "status": "PUBLISHED",   "repo": "railway-n8n"},
    "railway-netdata":      {"code": "netdata-1",      "status": "PUBLISHED",   "repo": "railway-netdata"},
    "railway-node-red":     {"code": "node-red-2",     "status": "PUBLISHED",   "repo": "railway-node-red"},
    "railway-open-webui":   {"code": "open-webui-3",   "status": "PUBLISHED",   "repo": "railway-open-webui"},
    "railway-plausible":    {"code": "plausible-2",    "status": "PUBLISHED",   "repo": "railway-plausible"},
    "railway-pocketbase":   {"code": "pocketbase-5",   "status": "PUBLISHED",   "repo": "railway-pocketbase"},
    "railway-stirling-pdf": {"code": "stirling-pdf-1", "status": "PUBLISHED",   "repo": "railway-stirling-pdf"},
    "railway-syncthing":    {"code": "syncthing-1",    "status": "PUBLISHED",   "repo": "railway-syncthing"},
    "railway-whoogle-search": {"code": "whoogle-search", "status": "PUBLISHED", "repo": "railway-whoogle-search"},
}

def raw_github_url(repo, filename="og-image.svg"):
    """Get the raw GitHub URL for a file in the main branch."""
    return f"https://raw.githubusercontent.com/INAPP-Mobile/{repo}/main/{filename}"

def fix_readme_deploy_link(dirname, code, readme_path):
    """Fix the deploy-on-railway link in the README."""
    if not code:
        print(f"  SKIP: no published code for {dirname}")
        return False
    
    with open(readme_path) as f:
        content = f.read()
    
    original = content
    correct_url = f"https://railway.app/template/{code}"
    correct_md = f"[![Deploy on Railway](https://railway.app/button.svg)]({correct_url})"
    
    # Pattern 1: [![Deploy on Railway](...)](ANY_URL)
    # Match the deploy button link pattern
    pattern = r'\[!\[Deploy on Railway\]\([^)]+\)\]\(https?://(?:railway\.app|railway\.com)[^)]+\)'
    
    def replace_deploy_link(match):
        return f"[![Deploy on Railway](https://railway.app/button.svg)]({correct_url})"
    
    content = re.sub(pattern, replace_deploy_link, content)
    
    # Pattern 2: shields.io badge style deploy links
    # [![Deploy on Railway](https://img.shields.io/badge/Deploy%20on-Railway-...)](ANY_URL)
    pattern2 = r'\[!\[Deploy on Railway\]\(https://img\.shields\.io/badge/[^)]+\)\]\(https?://(?:railway\.app|railway\.com)[^)]+\)'
    content = re.sub(pattern2, replace_deploy_link, content)
    
    # Pattern 3: Deploy on Railway button.svg on railway.com
    pattern3 = r'\[!\[Deploy on Railway\]\(https://railway\.com/button[^)]*\)\]\(https?://railway\.com[^)]+\)'
    content = re.sub(pattern3, replace_deploy_link, content)
    
    # Pattern 4: Deploy button using button/deploy.svg
    pattern4 = r'\[!\[Deploy on Railway\]\(https://railway\.com/button/deploy\.svg\)\]\(https?://railway\.com[^)]+\)'
    content = re.sub(pattern4, replace_deploy_link, content)
    
    # Also replace any remaining railway.com deploy links in markdown link format
    # (catch-all for any we missed)
    if "railway.com" in content:
        # More specific: find any [text](railway.com/...) pattern 
        content = re.sub(
            r'\[([^\]]*Deploy[^\]]*)\]\(https?://railway\.com/(?:deploy|template)[^)]+\)',
            lambda m: f"[{m.group(1)}]({correct_url})",
            content
        )
    
    if content != original:
        with open(readme_path, 'w') as f:
            f.write(content)
        print(f"  FIXED deploy link -> {correct_url}")
        return True
    else:
        print(f"  Deploy link OK or no change needed")
        return False

def fix_readme_og_image(dirname, repo, readme_path):
    """Fix local og-image.svg references to use raw GitHub URLs."""
    with open(readme_path) as f:
        content = f.read()
    
    original = content
    raw_url = raw_github_url(repo, "og-image.svg")
    
    # Pattern: ![OG Image](og-image.svg) or ![Something](og-image.svg)
    # Replace local og-image.svg references with raw GitHub URLs
    content = re.sub(
        r'(!\[.*?\]\()(\./)?og-image\.svg(\))',
        lambda m: f"{m.group(1)}{raw_url}{m.group(3)}",
        content
    )
    
    # Also handle ./og-image.svg
    content = re.sub(
        r'(<img[^>]*src=")(\./)?og-image\.svg(")',
        lambda m: f'{m.group(1)}{raw_url}{m.group(3)}',
        content
    )
    
    if content != original:
        with open(readme_path, 'w') as f:
            f.write(content)
        print(f"  FIXED og-image URL -> raw GitHub URL")
        return True
    else:
        return False

def set_template_image(template_id, repo):
    """Publish an updated image URL to the template."""
    image_url = raw_github_url(repo, "og-image.svg")
    
    # First get the current template data
    tmpl = rgql.query_template(template_id)
    if not tmpl:
        print(f"  FAILED to query template {template_id}")
        return False
    
    # Check what the current publish image is
    print(f"  Current status: {tmpl.get('status')}")
    
    # Read the existing README for this template
    # We need to find the dirname from template_id
    dirname = None
    for d, info in TEMPLATES.items():
        tids = {
            "cd7fe649-01aa-4d70-9401-f0e3253ff3d4": "railway-arcane",
            "dcd5d52a-7aac-410e-bf31-de28d7143b64": "railway-beszel",
            "7587214b-da79-44d8-be3c-91ff2288306b": "railway-blinko",
            "a49fba65-83ea-441d-9e79-182af413569a": "railway-blocky",
            "df9e11be-469e-4a00-bdc4-4d425818c051": "railway-changedetection.io",
            "6dd024bc-bc19-4b42-bc32-5e97fc2ede33": "railway-filebrowser",
            "6e4b0fd3-24a7-4215-963e-ef1f8876be12": "railway-ghost",
            "bbb4fa08-e890-472a-8c0c-22b9c366d19f": "railway-gotify",
            "1f23a1ff-370a-4eae-b8c5-2806985d150d": "railway-homepage",
            "57127802-8196-468b-b6f4-cdfcd7e404b5": "railway-hoppscotch",
            "7f55a1d4-9af4-4f59-a465-d77ffa83b831": "railway-kanboard",
            "12eac690-8f8e-4093-8691-6ab6cc62ccbe": "railway-memos",
            "d0b077b6-86e3-4287-a05d-ce3ce8417ad9": "railway-n8n",
            "14e24aab-8d9b-42b2-b778-1fb9079b5f6a": "railway-netdata",
            "93eac73f-1ede-40da-9423-dd54da7e6c27": "railway-node-red",
            "ddf337c3-1dcb-4f24-8e8a-b15a41dcea66": "railway-open-webui",
            "fa1c0407-24e8-4b1f-b6c9-48e20126c8bf": "railway-plausible",
            "f13b9827-e4b2-473d-bb66-90e498cdba9e": "railway-pocketbase",
            "dce8dc2c-5b88-4a84-8fe5-c4f1dad58ddb": "railway-stirling-pdf",
            "20b17cb9-da55-42dd-9cfd-f7d433bd9edb": "railway-syncthing",
            "2c54b909-b34f-47c2-90a1-c8525c205478": "railway-whoogle-search",
        }
        tid_map = {v: k for k, v in tids.items()}
        break
    
    # Map template_id to dirname
    tid_to_dir = {
        "cd7fe649-01aa-4d70-9401-f0e3253ff3d4": "railway-arcane",
        "dcd5d52a-7aac-410e-bf31-de28d7143b64": "railway-beszel",
        "7587214b-da79-44d8-be3c-91ff2288306b": "railway-blinko",
        "a49fba65-83ea-441d-9e79-182af413569a": "railway-blocky",
        "df9e11be-469e-4a00-bdc4-4d425818c051": "railway-changedetection.io",
        "6dd024bc-bc19-4b42-bc32-5e97fc2ede33": "railway-filebrowser",
        "6e4b0fd3-24a7-4215-963e-ef1f8876be12": "railway-ghost",
        "bbb4fa08-e890-472a-8c0c-22b9c366d19f": "railway-gotify",
        "1f23a1ff-370a-4eae-b8c5-2806985d150d": "railway-homepage",
        "57127802-8196-468b-b6f4-cdfcd7e404b5": "railway-hoppscotch",
        "7f55a1d4-9af4-4f59-a465-d77ffa83b831": "railway-kanboard",
        "12eac690-8f8e-4093-8691-6ab6cc62ccbe": "railway-memos",
        "d0b077b6-86e3-4287-a05d-ce3ce8417ad9": "railway-n8n",
        "14e24aab-8d9b-42b2-b778-1fb9079b5f6a": "railway-netdata",
        "93eac73f-1ede-40da-9423-dd54da7e6c27": "railway-node-red",
        "ddf337c3-1dcb-4f24-8e8a-b15a41dcea66": "railway-open-webui",
        "fa1c0407-24e8-4b1f-b6c9-48e20126c8bf": "railway-plausible",
        "f13b9827-e4b2-473d-bb66-90e498cdba9e": "railway-pocketbase",
        "dce8dc2c-5b88-4a84-8fe5-c4f1dad58ddb": "railway-stirling-pdf",
        "20b17cb9-da55-42dd-9cfd-f7d433bd9edb": "railway-syncthing",
        "2c54b909-b34f-47c2-90a1-c8525c205478": "railway-whoogle-search",
    }
    
    if template_id in tid_to_dir:
        dirname = tid_to_dir[template_id]
        readme_path = f"{BASE}/{dirname}/README.md"
        if os.path.exists(readme_path):
            with open(readme_path) as f:
                readme = f.read()
        else:
            readme = ""
    else:
        readme = ""
    
    # Use the publish mutation to update the image
    # Even though it's already published, calling publish again should update the image
    print(f"  Setting OG image: {image_url}")
    
    # Build the publish input
    pub_input = {
        "category": tmpl.get("category") or "Other",
        "description": tmpl.get("description") or "",
        "readme": readme or "",
        "image": image_url,
    }
    
    q = """
    mutation PublishTemplate($id: String!, $input: TemplatePublishInput!) {
        templatePublish(id: $id, input: $input) {
            id code name status image
        }
    }
    """
    r = rgql.gql(q, {"id": template_id, "input": pub_input})
    if r and "data" in r and r["data"].get("templatePublish"):
        result = r["data"]["templatePublish"]
        print(f"  PUBLISHED: code={result.get('code')}, name={result.get('name')}, image={result.get('image','')[:60]}...")
        return True
    else:
        print(f"  FAILED: {r}")
        return False


def main():
    # Step 1: Fix README deploy links and OG image references
    print("=" * 60)
    print("STEP 1: Fix README deploy links and OG image references")
    print("=" * 60)
    
    for dirname, info in TEMPLATES.items():
        readme_path = f"{BASE}/{dirname}/README.md"
        if not os.path.exists(readme_path):
            print(f"\n--- {dirname}: no README ---")
            continue
        
        code = info["code"]
        repo = info["repo"]
        status = info["status"]
        
        print(f"\n--- {dirname} (code={code}, status={status}) ---")
        
        if status != "PUBLISHED" or not code:
            print(f"  SKIP (not published or no code)")
            continue
        
        # Fix deploy link
        fix_readme_deploy_link(dirname, code, readme_path)
        
        # Fix OG image reference in README
        fix_readme_og_image(dirname, repo, readme_path)
    
    # Step 2: Check which published templates lack OG images and fix them
    print("\n" + "=" * 60)
    print("STEP 2: Check & fix OG images on published templates")
    print("=" * 60)
    
    tid_to_dir = {
        "dcd5d52a-7aac-410e-bf31-de28d7143b64": "railway-beszel",
        "7587214b-da79-44d8-be3c-91ff2288306b": "railway-blinko",
        "a49fba65-83ea-441d-9e79-182af413569a": "railway-blocky",
        "df9e11be-469e-4a00-bdc4-4d425818c051": "railway-changedetection.io",
        "6dd024bc-bc19-4b42-bc32-5e97fc2ede33": "railway-filebrowser",
        "6e4b0fd3-24a7-4215-963e-ef1f8876be12": "railway-ghost",
        "bbb4fa08-e890-472a-8c0c-22b9c366d19f": "railway-gotify",
        "1f23a1ff-370a-4eae-b8c5-2806985d150d": "railway-homepage",
        "57127802-8196-468b-b6f4-cdfcd7e404b5": "railway-hoppscotch",
        "7f55a1d4-9af4-4f59-a465-d77ffa83b831": "railway-kanboard",
        "12eac690-8f8e-4093-8691-6ab6cc62ccbe": "railway-memos",
        "d0b077b6-86e3-4287-a05d-ce3ce8417ad9": "railway-n8n",
        "14e24aab-8d9b-42b2-b778-1fb9079b5f6a": "railway-netdata",
        "93eac73f-1ede-40da-9423-dd54da7e6c27": "railway-node-red",
        "ddf337c3-1dcb-4f24-8e8a-b15a41dcea66": "railway-open-webui",
        "fa1c0407-24e8-4b1f-b6c9-48e20126c8bf": "railway-plausible",
        "f13b9827-e4b2-473d-bb66-90e498cdba9e": "railway-pocketbase",
        "dce8dc2c-5b88-4a84-8fe5-c4f1dad58ddb": "railway-stirling-pdf",
        "20b17cb9-da55-42dd-9cfd-f7d433bd9edb": "railway-syncthing",
        "2c54b909-b34f-47c2-90a1-c8525c205478": "railway-whoogle-search",
        "cd7fe649-01aa-4d70-9401-f0e3253ff3d4": "railway-arcane",
    }
    
    for tid, dirname in tid_to_dir.items():
        info = TEMPLATES.get(dirname, {})
        code = info.get("code")
        repo = info.get("repo", dirname)
        status = info.get("status")
        
        if status != "PUBLISHED" or not code:
            print(f"\n--- {dirname}: SKIP (status={status}) ---")
            continue
        
        print(f"\n--- {dirname} (code={code}) ---")
        
        # Query current template state
        tmpl = rgql.query_template(tid)
        if not tmpl:
            print(f"  FAILED to query")
            continue
        
        sc = tmpl.get("serializedConfig", {})
        if isinstance(sc, str):
            sc = json.loads(sc)
        
        # Check if the template has an image
        has_image = False
        if isinstance(sc, dict):
            # SerializedConfig may contain image info
            pass
        
        # Also check the publish endpoint
        # We need to use a different query to check the published image
        # For now, just set the image on templates we know are missing it
        templates_missing_image = [
            "changedetectionio-1", "filebrowser", "railway-n8n", 
            "open-webui-3", "pocketbase-5", "syncthing-1",
            "kanboard-2", "gotify", "whoogle-search",
            "node-red-2", "beszel", "blinko",
        ]
        
        needs_image = code in templates_missing_image
        
        if needs_image:
            print(f"  Needs OG image update")
            set_template_image(tid, repo)
        else:
            print(f"  OG image OK (or skipping)")


if __name__ == "__main__":
    main()
