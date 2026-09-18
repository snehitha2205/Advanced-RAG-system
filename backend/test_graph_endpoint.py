"""Test script to verify /api/graph/network endpoint returns data correctly."""
import urllib.request, json, sys

try:
    req = urllib.request.Request(
        'http://localhost:5000/api/graph/network',
        data=json.dumps({'filters': {}, 'limit': 200}).encode(),
        headers={'Content-Type': 'application/json'}
    )
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read())
    
    nodes = data.get('nodes', [])
    edges = data.get('edges', [])
    
    print(f"HTTP Status: {resp.status}")
    print(f"Nodes returned: {len(nodes)}")
    print(f"Edges returned: {len(edges)}")
    
    if nodes:
        print(f"\n--- First Node Preview ---")
        print(json.dumps(nodes[0], indent=2))
        print(f"\nNode keys: {list(nodes[0].keys())}")
        print(f"Node 'id' field: {nodes[0].get('id', 'MISSING!')}")
        
        # Check all required fields for Cytoscape
        print(f"\n--- Required Field Check ---")
        import_check = []
        for n in nodes:
            if not n.get('id'):
                import_check.append(f"Node missing 'id': {n}")
        for e in edges:
            if not e.get('source'):
                import_check.append(f"Edge missing 'source': {e}")
            if not e.get('target'):
                import_check.append(f"Edge missing 'target': {e}")
            # Check source/target match node ids
            node_ids = set(n.get('id') for n in nodes)
            if e.get('source') not in node_ids:
                import_check.append(f"Edge source '{e.get('source')}' not in nodes!")
            if e.get('target') not in node_ids:
                import_check.append(f"Edge target '{e.get('target')}' not in nodes!")
        
        if import_check:
            print("ISSUES FOUND:")
            for issue in import_check[:10]:
                print(f"  ⚠ {issue}")
        else:
            print("✅ All nodes have 'id' field")
            print("✅ All edges have 'source' and 'target' fields")
            print("✅ All edge source/target reference valid node IDs")
    else:
        print("\n⚠ No nodes returned!")
        print(f"Full response: {json.dumps(data, indent=2)[:500]}")
        
    if edges:
        print(f"\n--- First Edge Preview ---")
        print(json.dumps(edges[0], indent=2))
        print(f"\nEdge keys: {list(edges[0].keys())}")
        
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

