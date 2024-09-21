#!/bin/sh

# This script is used to adopt pre-existing pvcs into a Helm release. It is used in the
# following way:
#  helm-adpot.sh <namespace> <release-name>

[ "$#" -eq 2 ] || { echo "Usage: $0 <namespace> <release-name>"; exit 1; }

NAMESPACE=$1
RELEASE_NAME=$2
kubectl get -n $NAMESPACE pvc -o name | xargs -I % kubectl label -n $NAMESPACE % app.kubernetes.io/managed-by=Helm
kubectl get -n $NAMESPACE pvc -o name | xargs -I % kubectl annotate -n $NAMESPACE % meta.helm.sh/release-name=$RELEASE_NAME
kubectl get -n $NAMESPACE pvc -o name | xargs -I % kubectl annotate -n $NAMESPACE % meta.helm.sh/release-namespace=$NAMESPACE
kubectl get -n $NAMESPACE pvc -o name | xargs -I % kubectl annotate -n $NAMESPACE % helm.sh/resource-policy=keep
