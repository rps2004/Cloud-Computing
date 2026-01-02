ASSIGNMENT README — Reproducing experiments (Docker Swarm & Kubernetes)
========================================================================

Repository layout (top-level)
-----------------------------
ASSGN1_REPORT/        # Paper / LaTeX files
code/                 # All source code and manifests (server, client, k8s yamls, tests)
test/                 # Test outputs, plots, screenshots (image files)
README.txt            # this file

Example tree (what you should see)
----------------------------------
ASSGN1_REPORT
code
  ├─ client.py
  ├─ server.py
  ├─ Dockerfile
  ├─ k8s-deployment.yaml
  ├─ k8s-hpa.yaml
  ├─ requirements.txt
test
  ├─ test_res_single
  ├─ test_res_swarm3
  ├─ test_res_swarm5
  └─ tes_res_scaling

IMPORTANT: image name must always be exactly: reverse-string

Prerequisites
-------------
- Docker / Docker Desktop installed and running
- Docker Swarm (Docker Desktop includes it)
- Minikube (local Kubernetes)
- kubectl (compatible with minikube)
- Python 3 (to run client.py)

If using minikube, recommended start (adjust CPU/RAM to your machine):
minikube start --driver=docker --cpus=4 --memory=8192

----------------------------------------------------------------------
PART A — Single container (baseline)
----------------------------------------------------------------------
1) Build the image:
cd code
docker build -t reverse-string .

2) Run single container (host port 5000 -> container 5000):
docker run --rm -p 5000:5000 --name reverse-single reverse-string

3) Run client test (example(open another terminal, current directory should be code)):
python client.py --target swarm --swarm-url http://127.0.0.1:5000/reverse --count 10000 --rate 100 --concurrency 150

4) Capture docker stats (snapshot):
docker stats --no-stream > docker_stats_single.txt

5) Stop container (if backgrounded):
docker stop reverse-single

----------------------------------------------------------------------
PART B — Docker Swarm (3 replicas) and scale to 5
----------------------------------------------------------------------
1) Build the image:
cd code
docker build -t reverse-string .

2) Initialize swarm (if not already):
docker swarm init

3) Create the Swarm service (3 replicas, publish port 5000):
docker service create --name reverse-svc --publish published=5000,target=5000 --replicas=3 reverse-string

Check:
docker service ls
docker service ps reverse-svc

4) Run client against Swarm:
python client.py --target swarm --swarm-url http://127.0.0.1:5000/reverse --count 10000 --rate 100 --concurrency 150

5) Capture swarm stats:
docker stats --no-stream > docker_stats_swarm3_100.txt

6) Scale to 5 replicas:
docker service scale reverse-svc=5

Check:
docker service ps reverse-svc

7) Run client again (example):
python client.py --target swarm --swarm-url http://127.0.0.1:5000/reverse --count 10000 --rate 500 --concurrency 250

8) Remove service when done:
docker service rm reverse-svc

Note:If you notice any failures, its just that some request where piled up and couldnt be computed within time,
Inorder to remove any failures, change the concurrency and the rate accordingly or reduce the number of count.

----------------------------------------------------------------------
PART C — Kubernetes (LoadBalancer, port 52396)
----------------------------------------------------------------------
1) Build image and load into minikube:
cd code
docker build -t reverse-string .
minikube image load reverse-string

2) Apply deployment + LoadBalancer service:
kubectl apply -f k8s-deployment.yaml

3) Run minikube tunnel on another command prompt(as Administrator):
minikube tunnel

4) Check service:
kubectl get svc reverse-service

Example output:
NAME              TYPE           CLUSTER-IP      EXTERNAL-IP   PORT(S)          
reverse-service   LoadBalancer   10.108.158.16   127.0.0.1     52396:31417/TCP 

5) Run client (url made using external-ip:port/reverse):
python client.py --target k8s --k8s-url http://127.0.0.1:52396/reverse --count 10000 --rate 500 --concurrency 150

----------------------------------------------------------------------
PART D — Kubernetes Autoscaling (HPA)
----------------------------------------------------------------------
1) Apply HPA:
kubectl apply -f k8s-hpa.yaml


2) Watch HPA:
kubectl get hpa -w

3) Watch pods:
kubectl get pods -l app=reverse -w

4) Capture CPU/mem (PowerShell recommended):
kubectl top pods -l app=reverse --watch | Tee-Object metrics_autoscale.txt

5) Run client to trigger scale:
python client.py --target k8s --k8s-url http://127.0.0.1:52396/reverse --count 10000 --rate 50 --concurrency 75

Observe HPA scaling up/down.

----------------------------------------------------------------------
PART E — Collecting metrics (snapshots)
----------------------------------------------------------------------
Before:
kubectl top pods -l app=reverse > metrics_before.txt

During:
kubectl top pods -l app=reverse > metrics_during.txt

After:
kubectl top pods -l app=reverse > metrics_after.txt



----------------------------------------------------------------------
CLEANUP
----------------------------------------------------------------------
Remove Swarm service:
docker service rm reverse-svc

Delete Kubernetes resources:
kubectl delete -f code/k8s-deployment-loadbalancer.yaml
kubectl delete -f code/k8s-hpa-gradual.yaml

Stop tunnel:
Ctrl+C in the tunnel terminal

----------------------------------------------------------------------
TROUBLESHOOTING
----------------------------------------------------------------------
- Metrics not available:
  minikube addons enable metrics-server
- External-IP pending:
  run minikube tunnel as Administrator
- Port conflicts:
  Swarm uses 5000, Kubernetes uses 52396
- Very low CPU usage:
  the app is lightweight; use higher concurrency or add CPU work for demo
