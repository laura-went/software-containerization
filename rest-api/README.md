# Steps to run this:
1. Ensure `microk8s status` shows registry as enabled. If not, enable it.
2. `docker build -t localhost:32000/rest-api`
3. `docker push localhost:32000/rest-api`
4. `kubectl apply -f .`

Commands might need to be prefixed with `sudo`.

To list images in local registry: `microk8s ctr images list | grep localhost`

To delete an image in local registry: `microk8s ctr images rm <image>`