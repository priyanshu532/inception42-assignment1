#!/usr/bin/env python3
"""Safe completion helper for inception42-assignment1. Standard library only."""
import argparse, json, shutil, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'generated' / 'completion'

def cmd(args, required=True):
    print('+', ' '.join(map(str,args)), flush=True)
    r = subprocess.run(args, text=True, capture_output=True)
    if r.returncode and required:
        raise RuntimeError(r.stderr.strip() or 'command failed')
    if r.stdout.strip(): print(r.stdout.strip()[:2500])
    if r.returncode: print('NOT READY:', r.stderr.strip()[:500])
    return r.returncode == 0

def emit(name, content):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/name).write_text(content.strip()+'\n')
    print('Generated:', OUT/name)

def generate():
    emit('prod-namespace.yaml', '''
apiVersion: v1
kind: Namespace
metadata:
  name: inception-prod
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
''')
    emit('prod-pvc.yaml', '''
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: qwen-model-pvc
  namespace: inception-prod
spec:
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 2Gi
''')
    emit('prod-default-deny.yaml', '''
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: inception-prod
spec:
  podSelector: {}
  policyTypes: [Ingress, Egress]
''')

    dev_policies = (
        ROOT / 'k8s/network-policies/10-allow-traffic.yaml'
    ).read_text()

    emit(
        'prod-allow-services.yaml',
        dev_policies.replace(
            'namespace: inception-dev',
            'namespace: inception-prod'
        )
    )

    emit('prod-hpa.yaml', '''
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: gateway-hpa
  namespace: inception-prod
spec:
  scaleTargetRef: {apiVersion: apps/v1, kind: Deployment, name: gateway}
  minReplicas: 1
  maxReplicas: 3
  metrics:
    - type: Resource
      resource:
        name: cpu
        target: {type: Utilization, averageUtilization: 70}
''')
    emit('prod-pdb.yaml', '''
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: gateway-pdb
  namespace: inception-prod
spec:
  minAvailable: 1
  selector: {matchLabels: {app: gateway}}
''')
    emit('dev-gateway-policy-CANDIDATE.yaml', '''
# REVIEW BEFORE APPLYING: hostNetwork source IP may be CNI-specific.
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-gateway-ingress
  namespace: inception-dev
spec:
  podSelector: {matchLabels: {app: gateway}}
  policyTypes: [Ingress]
  ingress:
    - from:
        - ipBlock: {cidr: 172.18.0.3/32}
      ports: [{protocol: TCP, port: 8000}]
''')
    emit('README.txt', '''
Safe automation boundaries:
- --dry-run generates and validates manifests; no Kubernetes changes.
- --apply installs production namespace, PVC, NetworkPolicies, HPA and PDB ONLY.
- Production app/LLM is NOT started: the prod PVC needs a downloaded model first.
- Production network policy requires review before deploying workloads.
- HPA requires a working metrics-server (not installed by this script).
- PDB minAvailable=1 on a single replica prevents voluntary eviction.
- Dev gateway candidate is NOT applied: test hostNetwork source address first.
- CI security scans, observability and air-gapped Assignment 2 remain manual.
- --verify checks resources and writes verification.json.
''')

def verify():
    checks = {
      'cluster': ['kubectl','get','nodes'],
      'dev pods': ['kubectl','get','pods','-n','inception-dev'],
      'traefik': ['kubectl','get','pods','-n','traefik'],
      'dev policies': ['kubectl','get','networkpolicy','-n','inception-dev'],
      'prod namespace': ['kubectl','get','namespace','inception-prod'],
      'prod resources': ['kubectl','get','deployment,hpa,pdb,pvc','-n','inception-prod'],
      'metrics API': ['kubectl','get','--raw','/apis/metrics.k8s.io/v1beta1/nodes'],
    }
    results={}
    for label, args in checks.items():
        print('\nCHECK:',label)
        results[label]=cmd(args, required=False)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'verification.json').write_text(json.dumps(results,indent=2))
    print('\nReport:', OUT/'verification.json')

def main():
    p=argparse.ArgumentParser()
    mode=p.add_mutually_exclusive_group()
    mode.add_argument('--dry-run',action='store_true')
    mode.add_argument('--apply',action='store_true')
    mode.add_argument('--verify',action='store_true')
    a=p.parse_args()
    for f in ('helm/inception-app/Chart.yaml','helm/inception-app/values.yaml','helm/inception-app/values-prod.yaml'):
        if not (ROOT/f).exists(): raise RuntimeError('Missing '+f+'; put script in project root')
    for executable in ('helm','kubectl'):
        if not shutil.which(executable): raise RuntimeError(executable+' is missing from PATH')
    if a.verify: verify(); return
    generate()
    cmd(['helm','template','inception-prod',str(ROOT/'helm/inception-app'),'-n','inception-prod','-f',str(ROOT/'helm/inception-app/values.yaml'),'-f',str(ROOT/'helm/inception-app/values-prod.yaml')])
    if a.apply:
        for f in ('prod-namespace.yaml','prod-pvc.yaml','prod-default-deny.yaml','prod-allow-services.yaml','prod-hpa.yaml','prod-pdb.yaml'):
            cmd(['kubectl','apply','-f',str(OUT/f)])
        verify()
    else: print('\nDRY RUN PASSED. No cluster changes. Read generated/completion/README.txt before --apply.')

if __name__=='__main__':
    try: main()
    except (RuntimeError, OSError) as e:
        print('ERROR:',e,file=sys.stderr); sys.exit(1)
