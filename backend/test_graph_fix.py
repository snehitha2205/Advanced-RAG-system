"""Test graph retrieval fix - no unicode chars."""
import urllib.request, json, sys, os

os.environ['PYTHONIOENCODING'] = 'utf-8'

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
    
    print("HTTP Status: {}".format(resp.status))
    print("Nodes returned: {}".format(len(nodes)))
    print("Edges returned: {}".format(len(edges)))
    
    if nodes:
        node_keys = list(nodes[0].keys())
        print("\nFirst node keys: {}".format(node_keys))
        print("First node id: '{}'".format(nodes[0].get('id', 'MISSING!')))
        print("First node canonical_name: '{}'".format(nodes[0].get('canonical_name', 'MISSING!')))
        print("First node entity_type: '{}'".format(nodes[0].get('entity_type', 'MISSING!')))
        print("Sample node full: {}".format(json.dumps(nodes[0])))
        
        # Check for nodes missing critical fields
        missing_id = [n for n in nodes if not n.get('id')]
        missing_name = [n for n in nodes if not n.get('canonical_name')]
        if missing_id:
            print("\nWARNING: {} nodes missing 'id'!".format(len(missing_id)))
        if missing_name:
            print("\nWARNING: {} nodes missing 'canonical_name'!".format(len(missing_name)))
            
        # Edge validation
        if edges:
            print("\nFirst edge keys: {}".format(list(edges[0].keys())))
            print("First edge source: '{}'".format(edges[0].get('source', 'MISSING!')))
            print("First edge target: '{}'".format(edges[0].get('target', 'MISSING!')))
            print("First edge predicate: '{}'".format(edges[0].get('predicate', 'MISSING!')))
            
            # Check source/target exist in nodes
            node_ids = set(n.get('id') for n in nodes if n.get('id'))
            missing_sources = [e for e in edges if e.get('source') not in node_ids]
            missing_targets = [e for e in edges if e.get('target') not in node_ids]
            
            if missing_sources:
                print("\nERROR: {} edges have source not in nodes!".format(len(missing_sources)))
            if missing_targets:
                print("\nERROR: {} edges have target not in nodes!".format(len(missing_targets)))
            if not missing_sources and not missing_targets:
                print("\nAll edge source/target reference valid node IDs.")
        else:
            print("\nNo edges returned.")
    else:
        print("\nNo nodes returned!")
        print("Full response: {}".format(json.dumps(data, indent=2)[:500]))
        
except Exception as e:
    print("ERROR: {}".format(e))
    import traceback
    traceback.print_exc()
    sys.exit(1)

