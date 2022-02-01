# How to install
1. In microk8s, you need to enable: helm3, registry, storage
2. Enable TLS:
    1. Generate certificates with `openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout key.pem -out cert.pem -subj "/CN=hostname/O=hostname"`
        - for the default setup, `hostname` is `linkr.local` (change also in `linkr/values.yaml`)
    2. Create a secret with `kubectl create secret tls my-tls-secret --cert=cert.pem --key=key.pem`
    3. Enable ingress with TLS using `microk8s enable ingress:default-ssl-certificate=default/my-tls-secret`
    4. Add `127.0.0.1 linkr.local` to `/etc/hosts` to make `https://linkr.local` point to the Ingress
3. Build and push docker images:
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

4. Install the Helm chart with `helm install linkr linkr/`
