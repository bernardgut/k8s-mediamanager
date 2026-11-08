{{/*
Expand the name of the chart.
*/}}
{{- define "k8s-mediamanager.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "k8s-mediamanager.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "k8s-mediamanager.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "k8s-mediamanager.labels" -}}
helm.sh/chart: {{ include "k8s-mediamanager.chart" .context }}
{{ include "k8s-mediamanager.selectorLabels" . }}
{{- if .context.Chart.AppVersion }}
app.kubernetes.io/version: {{ .context.Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .context.Release.Service }}
{{- end }}

{{/*
Selector labels — includes both chart-level and component-level selectors
Accepts a dict with "context" (global context) and "component" (service name)
*/}}
{{- define "k8s-mediamanager.selectorLabels" -}}
app.kubernetes.io/name: {{ include "k8s-mediamanager.name" .context }}
app.kubernetes.io/instance: {{ .context.Release.Name }}
{{- end }}

{{/*
Service selector labels — adds the `app` discriminator so services select only their own pods.
Pre-existing Deployments cannot adopt it (spec.selector is immutable); new components use it.
*/}}
{{- define "k8s-mediamanager.serviceSelectorLabels" -}}
app.kubernetes.io/name: {{ include "k8s-mediamanager.name" .context }}
app.kubernetes.io/instance: {{ .context.Release.Name }}
app: {{ .component }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "k8s-mediamanager.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "k8s-mediamanager.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{/* ────────────────────────────────────────────────────────────────────────── */}}
{{/* Persistence claim name — returns existingClaim if set, else generated name */}}
{{/* Accepts: .context (global), .component (name), .persistence (values block) */}}
{{/* ────────────────────────────────────────────────────────────────────────── */}}
{{- define "k8s-mediamanager.persistenceClaimName" -}}
{{- if .persistence.existingClaim -}}
{{- .persistence.existingClaim -}}
{{- else -}}
{{- include "k8s-mediamanager.fullname" .context -}}-{{ .component -}}
{{- end -}}
{{- end }}

{{/* ────────────────────────────────────────────────────────────────────────── */}}
{{/* PVC — reusable PersistentVolumeClaim template                              */}}
{{/* Skipped when persistence.existingClaim is set                             */}}
{{/* Accepts: .context (global), .component (name), .persistence (values block) */}}
{{/* ────────────────────────────────────────────────────────────────────────── */}}
{{- define "k8s-mediamanager.pvc" -}}
{{- if not .persistence.existingClaim }}
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {{ include "k8s-mediamanager.fullname" .context }}-{{ .component }}
  labels:
    {{- include "k8s-mediamanager.labels" (dict "context" .context "component" .component) | nindent 4 }}
  {{- with .persistence.annotations }}
  annotations:
    {{- toYaml . | nindent 4 }}
  {{- end }}
spec:
  accessModes:
    {{- toYaml .persistence.accessModes | nindent 4 }}
  resources:
    requests:
      storage: {{ .persistence.size }}
  {{- if .persistence.storageClassName }}
  storageClassName: {{ .persistence.storageClassName }}
  {{- end }}
  {{- with .persistence.selector }}
  selector:
    {{- toYaml . | nindent 4 }}
  {{- end }}
{{- end }}
{{- end }}

{{/* ────────────────────────────────────────────────────────────────────────── */}}
{{/* *arr init ConfigMap — config.xml + init script                            */}}
{{/* Accepts: .context, .component, .values (service values block)             */}}
{{/* ────────────────────────────────────────────────────────────────────────── */}}
{{- define "k8s-mediamanager.arr.configmap" -}}
apiVersion: v1
kind: ConfigMap
metadata:
  name: {{ include "k8s-mediamanager.fullname" .context }}-init-{{ .component }}
  labels:
    {{- include "k8s-mediamanager.labels" (dict "context" .context "component" .component) | nindent 4 }}
data:
  config.xml: |
    <Config>
      <UrlBase>{{ .values.ingress.path }}</UrlBase>
      <Port>{{ .values.service.port }}</Port>
      <ApiKey>{{ .values.apiKey }}</ApiKey>
      <InstanceName>{{ .values.instanceName }}</InstanceName>
      <LogLevel>{{ .values.logLevel | default "info" }}</LogLevel>
    </Config>
  init-{{ .component }}.sh: |
    #!/bin/sh
    echo "### Initializing config ###"
    if [ ! -f /{{ .component }}-config/config.xml ]; then
      cp -n /init-{{ .component }}/config.xml /{{ .component }}-config/config.xml
      echo "### No configuration found, initialized with default settings ###"
    fi
{{- end }}

{{/* ────────────────────────────────────────────────────────────────────────── */}}
{{/* Pod security context — shared by all services                             */}}
{{/* ────────────────────────────────────────────────────────────────────────── */}}
{{- define "k8s-mediamanager.podSecurityContext" -}}
runAsNonRoot: true
runAsUser: {{ .Values.global.puid }}
runAsGroup: {{ .Values.global.pgid }}
fsGroup: {{ .Values.global.pgid }}
{{- /* WARNING: without OnRootMismatch, linstor-csi >=2.12 (CSIDriver fsGroupPolicy
File) chown-walks the entire RWX media export on every pod start. */}}
fsGroupChangePolicy: OnRootMismatch
seccompProfile:
  type: RuntimeDefault
{{- end }}

{{/* ────────────────────────────────────────────────────────────────────────── */}}
{{/* Container security context — hardened, shared by all containers           */}}
{{/* ────────────────────────────────────────────────────────────────────────── */}}
{{- define "k8s-mediamanager.containerSecurityContext" -}}
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
capabilities:
  drop:
    - ALL
{{- end }}

{{/* ────────────────────────────────────────────────────────────────────────── */}}
{{/* Init container — copies config.xml if missing                             */}}
{{/* Accepts: .context, .component                                             */}}
{{/* ────────────────────────────────────────────────────────────────────────── */}}
{{- define "k8s-mediamanager.arr.initContainer" -}}
- name: config-{{ .component }}
  image: "{{ .context.Values.global.initImage.repository }}:{{ .context.Values.global.initImage.tag }}"
  imagePullPolicy: {{ .context.Values.global.initImage.pullPolicy }}
  command: ["/init-{{ .component }}/init-{{ .component }}.sh"]
  volumeMounts:
    - name: init-files
      mountPath: /init-{{ .component }}
    - name: config
      mountPath: /{{ .component }}-config
  securityContext:
    {{- include "k8s-mediamanager.containerSecurityContext" . | nindent 4 }}
  resources:
    requests:
      cpu: "10m"
      memory: "16Mi"
    limits:
      cpu: "100m"
      memory: "64Mi"
{{- end }}

{{/* ────────────────────────────────────────────────────────────────────────── */}}
{{/* Common environment variables for all services                             */}}
{{/* ────────────────────────────────────────────────────────────────────────── */}}
{{- define "k8s-mediamanager.commonEnv" -}}
- name: PUID
  value: "{{ .Values.global.puid }}"
- name: PGID
  value: "{{ .Values.global.pgid }}"
- name: TZ
  value: "{{ .Values.global.timezone }}"
{{- end }}

{{/* ────────────────────────────────────────────────────────────────────────── */}}
{{/* Exportarr metrics sidecar container                                       */}}
{{/* Accepts: .context, .component, .values (service values), .metricsArg      */}}
{{/* ────────────────────────────────────────────────────────────────────────── */}}
{{- define "k8s-mediamanager.metrics.exportarr" -}}
- name: metrics
  securityContext:
    {{- include "k8s-mediamanager.containerSecurityContext" . | nindent 4 }}
  image: "{{ .values.metrics.image.repository }}:{{ .values.metrics.image.tag }}"
  imagePullPolicy: {{ .values.metrics.image.pullPolicy }}
  args:
    - {{ .component }}
  env:
    - name: PORT
      value: {{ .values.metrics.port | quote }}
    - name: URL
      value: "http://localhost:{{ .values.service.port }}{{ .values.ingress.path }}"
    - name: APIKEY
      value: {{ .values.apiKey }}
    {{- with .extraEnv }}
    {{- toYaml . | nindent 4 }}
    {{- end }}
  ports:
    - name: metrics
      containerPort: {{ .values.metrics.port }}
  {{- /* /healthz answers locally; /metrics would fan out to the *arr API on every probe. */}}
  livenessProbe:
    httpGet:
      path: /healthz
      port: metrics
    initialDelaySeconds: 15
    periodSeconds: 30
    timeoutSeconds: 10
  readinessProbe:
    httpGet:
      path: /healthz
      port: metrics
    initialDelaySeconds: 15
    periodSeconds: 30
    timeoutSeconds: 10
  # exportarr is a tiny metrics scraper; sensible bounded default so the sidecar
  # is never the limitless container (p0 require-resources). Override per app via
  # <component>.metrics.resources.
  resources:
    {{- toYaml (.values.metrics.resources | default (dict "requests" (dict "cpu" "10m" "memory" "32Mi") "limits" (dict "cpu" "100m" "memory" "64Mi"))) | nindent 4 }}
{{- end }}

{{/* ────────────────────────────────────────────────────────────────────────── */}}
{{/* Service — reusable Service template                                       */}}
{{/* Accepts: .context, .component, .values (service values)                   */}}
{{/* Optional: .extraPorts (list of additional port dicts)                      */}}
{{/* ────────────────────────────────────────────────────────────────────────── */}}
{{- define "k8s-mediamanager.service" -}}
apiVersion: v1
kind: Service
metadata:
  name: {{ include "k8s-mediamanager.fullname" .context }}-{{ .component }}
  labels:
    {{- include "k8s-mediamanager.labels" (dict "context" .context "component" .component) | nindent 4 }}
spec:
  {{- if .ipFamilyPolicy }}
  ipFamilyPolicy: {{ .ipFamilyPolicy }}
  {{- else }}
  ipFamilyPolicy: {{ .context.Values.global.ipFamilyPolicy }}
  {{- end }}
  {{- if .ipFamilies }}
  ipFamilies:
    {{- toYaml .ipFamilies | nindent 4 }}
  {{- else if .context.Values.global.ipFamilies }}
  ipFamilies:
    {{- toYaml .context.Values.global.ipFamilies | nindent 4 }}
  {{- end }}
  type: {{ .serviceType | default "ClusterIP" }}
  ports:
    - name: {{ .component }}-port
      port: {{ .port }}
      targetPort: {{ .targetPort | default .port }}
      protocol: TCP
      {{- if .nodePort }}
      nodePort: {{ .nodePort }}
      {{- end }}
    {{- range .extraPorts }}
    - name: {{ .name }}
      port: {{ .port }}
      targetPort: {{ .targetPort | default .port }}
      protocol: {{ .protocol | default "TCP" }}
      {{- if .nodePort }}
      nodePort: {{ .nodePort }}
      {{- end }}
    {{- end }}
  selector:
    {{- include "k8s-mediamanager.serviceSelectorLabels" (dict "context" .context "component" .component) | nindent 4 }}
{{- end }}

{{/* ────────────────────────────────────────────────────────────────────────── */}}
{{/* HTTPRoute — reusable Gateway API HTTPRoute                                */}}
{{/* Accepts: .context, .component, .gatewayName, .gatewayNamespace,           */}}
{{/*          .hostname, .path, .port                                          */}}
{{/* ────────────────────────────────────────────────────────────────────────── */}}
{{- define "k8s-mediamanager.httproute" -}}
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: {{ include "k8s-mediamanager.fullname" .context }}-{{ .component }}
  labels:
    {{- include "k8s-mediamanager.labels" (dict "context" .context "component" .component) | nindent 4 }}
spec:
  parentRefs:
    - name: {{ .gatewayName }}
      namespace: {{ .gatewayNamespace }}
  hostnames:
    - {{ .hostname | quote }}
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: {{ .path }}
      backendRefs:
        - name: {{ include "k8s-mediamanager.fullname" .context }}-{{ .component }}
          port: {{ .port }}
{{- end }}

{{/* ────────────────────────────────────────────────────────────────────────── */}}
{{/* ServiceMonitor — reusable Prometheus ServiceMonitor                       */}}
{{/* Accepts: .context, .component                                             */}}
{{/* Optional: .extraEndpoints (list of additional endpoint dicts)             */}}
{{/* ────────────────────────────────────────────────────────────────────────── */}}
{{- define "k8s-mediamanager.servicemonitor" -}}
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: {{ include "k8s-mediamanager.fullname" .context }}-{{ .component }}
  labels:
    {{- include "k8s-mediamanager.labels" (dict "context" .context "component" .component) | nindent 4 }}
spec:
  selector:
    matchLabels:
      {{- include "k8s-mediamanager.selectorLabels" (dict "context" .context "component" .component) | nindent 6 }}
  endpoints:
    - port: metrics
      scheme: http
      path: /metrics
    {{- range .extraEndpoints }}
    - port: {{ .port }}
      scheme: {{ .scheme | default "http" }}
      path: {{ .path | default "/metrics" }}
    {{- end }}
{{- end }}

{{/* ────────────────────────────────────────────────────────────────────────── */}}
{{/* *arr Deployment — full deployment for radarr/sonarr/lidarr/prowlarr       */}}
{{/* Accepts: .context, .component, .values (service values)                   */}}
{{/* Optional: .extraContainers, .extraVolumes, .extraInitContainers           */}}
{{/* ────────────────────────────────────────────────────────────────────────── */}}
{{- define "k8s-mediamanager.arr.deployment" -}}
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "k8s-mediamanager.fullname" .context }}-{{ .component }}
  labels:
    {{- include "k8s-mediamanager.labels" (dict "context" .context "component" .component) | nindent 4 }}
spec:
  strategy:
    type: Recreate
  replicas: 1
  selector:
    matchLabels:
      {{- include "k8s-mediamanager.selectorLabels" (dict "context" .context "component" .component) | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "k8s-mediamanager.selectorLabels" (dict "context" .context "component" .component) | nindent 8 }}
        app: {{ .component }}
    spec:
      {{- /* Outlasts the .NET host shutdown timeout (up to 30 s) so the app exits on its own. In-flight
      imports are still abandoned (non-atomic copies leave a truncated file): roll with an idle queue. */}}
      {{- $grace := .values.terminationGracePeriodSeconds }}
      terminationGracePeriodSeconds: {{ kindIs "invalid" $grace | ternary 120 $grace | int }}
      {{- if .context.Values.serviceAccount.create }}
      serviceAccountName: {{ include "k8s-mediamanager.serviceAccountName" .context }}
      {{- end }}
      securityContext:
        {{- include "k8s-mediamanager.podSecurityContext" .context | nindent 8 }}
      initContainers:
        {{- include "k8s-mediamanager.arr.initContainer" (dict "context" .context "component" .component) | nindent 8 }}
        {{- with .extraInitContainers }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
      containers:
        - name: {{ .component }}
          securityContext:
            runAsUser: {{ .context.Values.global.puid }}
            runAsGroup: {{ .context.Values.global.pgid }}
            {{- include "k8s-mediamanager.containerSecurityContext" . | nindent 12 }}
          env:
            {{- include "k8s-mediamanager.commonEnv" .context | nindent 12 }}
            {{- with .values.extraEnv }}
            {{- toYaml . | nindent 12 }}
            {{- end }}
          image: "{{ .values.image.repository }}:{{ .values.image.tag }}"
          imagePullPolicy: {{ .values.image.pullPolicy }}
          {{- /* 5 min for database migrations after an image bump; liveness would kill them. */}}
          startupProbe:
            httpGet:
              path: {{ .values.ingress.path }}
              port: {{ .values.service.port }}
            periodSeconds: 10
            timeoutSeconds: 10
            failureThreshold: 30
          livenessProbe:
            httpGet:
              path: {{ .values.ingress.path }}
              port: {{ .values.service.port }}
            initialDelaySeconds: 15
            timeoutSeconds: 10
          readinessProbe:
            httpGet:
              path: {{ .values.ingress.path }}
              port: {{ .values.service.port }}
            initialDelaySeconds: 15
            timeoutSeconds: 10
          ports:
            - name: {{ .component }}-port
              containerPort: {{ .values.service.port }}
              protocol: TCP
          volumeMounts:
            - name: config
              mountPath: /config
            - name: tmp
              mountPath: /tmp
            {{- $data := trimSuffix "/" (.values.dataMountPath | default "") }}
            {{- range .values.mediaSubPaths }}
            {{- $sub := trimSuffix "/" (.mountPath | default "") }}
            {{- /* a sub-path mount at or inside the data mount splits it again, so link() fails with EXDEV */}}
            {{- if and $data (or (eq $sub $data) (hasPrefix (printf "%s/" $data) $sub) (hasPrefix (printf "%s/" $sub) $data)) }}
            {{- fail (printf "%s.dataMountPath %s overlaps mediaSubPaths mountPath %s" $.component $data .mountPath) }}
            {{- end }}
            - name: media
              mountPath: {{ .mountPath | quote }}
              subPath: {{ .subPath | quote }}
            {{- end }}
            {{- with .values.dataMountPath }}
            - name: media
              mountPath: {{ . | quote }}
            {{- end }}
            {{- with .values.extraVolumeMounts }}
            {{- toYaml . | nindent 12 }}
            {{- end }}
          {{- with .values.resources }}
          resources:
            {{- toYaml . | nindent 12 }}
          {{- end }}
        {{- if .values.metrics.enabled }}
        {{- include "k8s-mediamanager.metrics.exportarr" (dict "context" .context "component" .component "values" .values "extraEnv" .metricsExtraEnv) | nindent 8 }}
        {{- end }}
        {{- with .extraContainers }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
      volumes:
        - name: media
          persistentVolumeClaim:
            claimName: {{ .context.Values.sharedStorage.existingClaim }}
        - name: config
          persistentVolumeClaim:
            claimName: {{ include "k8s-mediamanager.persistenceClaimName" (dict "context" .context "component" .component "persistence" .values.persistence) }}
        - name: init-files
          configMap:
            defaultMode: 493
            name: {{ include "k8s-mediamanager.fullname" .context }}-init-{{ .component }}
        - name: tmp
          emptyDir: {}
        {{- with .extraVolumes }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
        {{- with .values.extraVolumes }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
      {{- with .values.nodeSelector }}
      nodeSelector:
        {{- toYaml . | nindent 8 }}
      {{- end }}
{{- end }}

{{/* ────────────────────────────────────────────────────────────────────────── */}}
{{/* Cleanuparr settings as code: the app version the reconciler was written    */}}
{{/* for, read from the script so the two can never drift apart                */}}
{{/* ────────────────────────────────────────────────────────────────────────── */}}
{{- define "k8s-mediamanager.cleanuparr.supportedVersion" -}}
{{- $line := regexFind "SUPPORTED_APP_VERSION = \"[0-9]+\\.[0-9]+\\.[0-9]+\"" (.Files.Get "files/cleanuparr/apply_config.py") -}}
{{- if not $line }}{{ fail "files/cleanuparr/apply_config.py is missing from the chart package" }}{{ end -}}
{{- $line | trimPrefix "SUPPORTED_APP_VERSION = \"" | trimSuffix "\"" -}}
{{- end }}

{{/* "true" when Cleanuparr settings as code is on; tolerates cleanuparr.config: null */}}
{{- define "k8s-mediamanager.cleanuparr.configEnabled" -}}
{{- if and .Values.cleanuparr.enabled (.Values.cleanuparr.config | default dict).enabled }}true{{ end -}}
{{- end }}

{{/* Cleanuparr link to a chart component under .base (externalBaseUrl or the gateway), or "" */}}
{{/* Accepts: .base (https://host, may be ""), .values (component values block) */}}
{{- define "k8s-mediamanager.cleanuparr.externalUrl" -}}
{{- if and .base .values.ingress.enabled -}}
{{- printf "%s%s" .base (trimSuffix "/" .values.ingress.path) -}}
{{- end -}}
{{- end }}

{{/* ────────────────────────────────────────────────────────────────────────── */}}
{{/* Cleanuparr desired state (compact JSON) from cleanuparr.config; fromChart  */}}
{{/* items take URLs and credentials from this chart's components               */}}
{{/* ────────────────────────────────────────────────────────────────────────── */}}
{{- define "k8s-mediamanager.cleanuparr.desiredState" -}}
{{- $v := .Values -}}
{{- $cfg := $v.cleanuparr.config | default dict -}}
{{- $supported := include "k8s-mediamanager.cleanuparr.supportedVersion" . -}}
{{- $tag := toString $v.cleanuparr.image.tag -}}
{{- $tagVer := "" -}}
{{- if regexMatch "^v?[0-9]+\\.[0-9]+\\.[0-9]+(@sha256:[0-9a-f]{64})?$" $tag -}}
{{- $tagVer = regexFind "[0-9]+\\.[0-9]+\\.[0-9]+" $tag -}}
{{- end -}}
{{- if ne $tagVer $supported -}}
{{- fail (printf "cleanuparr.config supports Cleanuparr %s only, image tag is %s: follow README 'Upgrading Cleanuparr' and update files/cleanuparr/apply_config.py before bumping." $supported $tag) -}}
{{- end -}}
{{- $mode := $cfg.mode | default "apply" -}}
{{- if not (has (toString $mode) (list "apply" "plan")) -}}
{{- fail (printf "cleanuparr.config.mode must be apply or plan, got %v" $mode) -}}
{{- end -}}
{{- /* ASP.NET also maps DOTNET_ and ASPNETCORE_ prefixed variables onto the same setting. */ -}}
{{- range $v.cleanuparr.extraEnv -}}
{{- $value := lower (trim (toString (.value | default ""))) -}}
{{- if and (regexMatch "(?i)^((DOTNET|ASPNETCORE)_)?DATABASE_PROVIDER$" (toString .name)) (or .valueFrom (not (has $value (list "" "sqlite")))) -}}
{{- fail "cleanuparr.config writes the SQLite databases; remove DATABASE_PROVIDER from cleanuparr.extraEnv" -}}
{{- end -}}
{{- end -}}
{{- $base := "" -}}
{{- if $cfg.externalBaseUrl -}}
{{- $base = trimSuffix "/" (toString $cfg.externalBaseUrl) -}}
{{- else if $v.gateway.restricted.enabled -}}
{{- $base = printf "https://%s" $v.gateway.restricted.hostname -}}
{{- end -}}
{{- $fullname := include "k8s-mediamanager.fullname" . -}}
{{- $c := deepCopy $cfg -}}
{{- $_ := unset $c "enabled" -}}
{{- $_ = unset $c "resources" -}}
{{- $_ = unset $c "externalBaseUrl" -}}
{{- $_ = set $c "schema" 1 -}}
{{- $_ = set $c "appVersion" $supported -}}
{{- $_ = set $c "mode" $mode -}}
{{- $_ = set $c "auth" ($c.auth | default dict) -}}
{{- range $type, $spec := $c.arr -}}
{{- range $i, $inst := $spec.instances -}}
{{- $at := printf "cleanuparr.config.arr.%s.instances[%d]" $type $i -}}
{{- if $inst.fromChart -}}
{{- if not (has $type (list "sonarr" "radarr" "lidarr")) -}}
{{- fail (printf "%s.fromChart: only sonarr, radarr and lidarr are part of this chart" $at) -}}
{{- end -}}
{{- $app := index $v $type -}}
{{- if not $app.enabled -}}
{{- fail (printf "%s.fromChart: %s.enabled is false" $at $type) -}}
{{- end -}}
{{- if or (not $app.apiKey) (hasPrefix "CHANGEME" (toString $app.apiKey)) -}}
{{- fail (printf "%s.fromChart: set %s.apiKey first" $at $type) -}}
{{- end -}}
{{- if not (kindIs "invalid" $inst.apiKey) -}}
{{- fail (printf "%s.apiKey: fromChart takes it from %s.apiKey; remove one of them" $at $type) -}}
{{- end -}}
{{- $_ := set $inst "apiKey" (toString $app.apiKey) -}}
{{- if kindIs "invalid" $inst.url -}}
{{- $_ := set $inst "url" (printf "http://%s-%s:%v%s" $fullname $type $app.service.port (trimSuffix "/" $app.ingress.path)) -}}
{{- end -}}
{{- if kindIs "invalid" $inst.externalUrl -}}
{{- $_ := set $inst "externalUrl" (include "k8s-mediamanager.cleanuparr.externalUrl" (dict "base" $base "values" $app)) -}}
{{- end -}}
{{- end -}}
{{- $_ := unset $inst "fromChart" -}}
{{- end -}}
{{- end -}}
{{- range $i, $client := $c.downloadClients -}}
{{- $at := printf "cleanuparr.config.downloadClients[%d]" $i -}}
{{- $from := toString ($client.fromChart | default "") -}}
{{- if eq $from "qbittorrent" -}}
{{- $qb := $v.qbittorrent -}}
{{- if not $qb.enabled -}}
{{- fail (printf "%s.fromChart: qbittorrent.enabled is false" $at) -}}
{{- end -}}
{{- if not (and $qb.config.auth.username $qb.config.auth.password) -}}
{{- fail (printf "%s.fromChart: set qbittorrent.config.auth.username and .password first" $at) -}}
{{- end -}}
{{- range $key := list "typeName" "host" "urlBase" "username" "password" -}}
{{- if not (kindIs "invalid" (index $client $key)) -}}
{{- fail (printf "%s.%s: fromChart: qbittorrent derives it from this chart; remove one of them" $at $key) -}}
{{- end -}}
{{- end -}}
{{- $_ := set $client "typeName" "qbittorrent" -}}
{{- $_ = set $client "host" (printf "http://%s-qbittorrent:%v" $fullname $qb.service.webui.port) -}}
{{- $_ = set $client "urlBase" "" -}}
{{- $_ = set $client "username" (toString $qb.config.auth.username) -}}
{{- $_ = set $client "password" (toString $qb.config.auth.password) -}}
{{- if kindIs "invalid" $client.externalUrl -}}
{{- $_ = set $client "externalUrl" (include "k8s-mediamanager.cleanuparr.externalUrl" (dict "base" $base "values" $qb)) -}}
{{- end -}}
{{- else if $from -}}
{{- fail (printf "%s.fromChart: %q is not a chart component; use qbittorrent or remove it" $at $from) -}}
{{- end -}}
{{- $_ := unset $client "fromChart" -}}
{{- end -}}
{{- if and $c.auth.passwordHash (not $c.auth.username) -}}
{{- fail "cleanuparr.config.auth.passwordHash is set without auth.username" -}}
{{- end -}}
{{- toJson $c -}}
{{- end }}
