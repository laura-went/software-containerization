In microk8s, you need to enable: helm3, registry, storage

To enable TLS:
1. Generate certificates with `openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout key.pem -out cert.pem -subj "/CN=linkr.local/O=linkr.local"`
2. Create a secret with `kubectl create secret tls my-tls-secret --cert=cert.pem --key=key.pem`
3. Enable ingress with TLS using `microk8s enable ingress:default-ssl-certificate=default/my-tls-secret`
4. Add `127.0.0.1 linkr.local` to `/etc/hosts` to make `https://linkr.local` point to the Ingress
