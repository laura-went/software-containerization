# How to install
1. Install microk8s
2. In this guide, kubectl = `sudo microk8s kubectl`, and helm = `sudo microk8s helm3`
3. In microk8s, you need to enable: helm3, registry, storage with `microk8s enable helm3, registry, storage`
4. Enable TLS:
    1. Generate certificates with `openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout key.pem -out cert.pem -subj "/CN=hostname/O=hostname"`
        - for the default setup, `hostname` is `linkr.local` (change also in `linkr/values.yaml`)
    2. Create a secret with `kubectl create secret tls my-tls-secret --cert=cert.pem --key=key.pem`
    3. Enable ingress with TLS using `microk8s enable ingress:default-ssl-certificate=default/my-tls-secret`
    4. Add `127.0.0.1 linkr.local` to `/etc/hosts` to make `https://linkr.local` point to the Ingress
5. Enable RBAC:
   1. `microk8s enable rbac`
6. Build and push docker images:
    - rest-api:

      ```sh
      docker build -t rest-api:v2 docker-images/rest-api/
      docker tag rest-api:v2 localhost:32000/rest-api:latest
      docker push localhost:32000/rest-api:latest
      ```

    - frontend:

      ```sh
      docker build -t frontend:v2 docker-images/frontend/
      docker tag frontend:v2 localhost:32000/frontend:latest
      docker push localhost:32000/frontend:latest
      ```

7. Install the Helm chart with `sudo microk8s helm3 install linkr linkr/`
8. Linkr is now available through [https://linkr.local](https://linkr.local)

FAQ
1. If microk8s gives errors, try `sudo microk8s reset`
2. If the following error appears *Error: rendered manifests contain a resource that already exists. Unable to continue with install*
<br> For example for Persistent Volume, try the following commands:<br>
`kubectl get all`<br>
`kubectl get pv`<br>
`kubectl delete pv <pv_name> --grace-period=0 --force`<br>
`kubectl patch pv <pv_name> -p '{"metadata":{"finalizers":null}}'`