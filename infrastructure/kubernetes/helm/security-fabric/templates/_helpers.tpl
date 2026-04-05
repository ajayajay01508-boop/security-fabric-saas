{{/* Reusable deployment template for all Security Fabric services */}}
{{- define "security-fabric.deployment" -}}
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ .name }}
  namespace: {{ $.Values.global.namespace }}
  labels:
    app: {{ .name }}
    chart: {{ $.Chart.Name }}-{{ $.Chart.Version }}
    release: {{ $.Release.Name }}
spec:
  replicas: {{ .replicaCount }}
  selector:
    matchLabels:
      app: {{ .name }}
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: {{ .name }}
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/path: "/metrics"
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") $ | sha256sum }}
    spec:
      serviceAccountName: {{ .name }}
      terminationGracePeriodSeconds: 30
      containers:
        - name: {{ .name }}
          image: {{ $.Values.global.imageRegistry }}/{{ .image.name }}:{{ $.Values.global.imageTag }}
          imagePullPolicy: {{ $.Values.global.imagePullPolicy }}
          {{- if .ports }}
          ports:
            {{- range .ports }}
            - containerPort: {{ .containerPort }}
              name: {{ .name }}
            {{- end }}
          {{- end }}
          envFrom:
            - configMapRef:
                name: security-fabric-config
            - secretRef:
                name: {{ $.Values.secrets.apiGatewaySecretName }}
          resources:
            {{- toYaml .resources | nindent 12 }}
          {{- if .livenessProbe }}
          livenessProbe:
            {{- toYaml .livenessProbe | nindent 12 }}
          {{- end }}
          {{- if .readinessProbe }}
          readinessProbe:
            {{- toYaml .readinessProbe | nindent 12 }}
          {{- end }}
          lifecycle:
            preStop:
              exec:
                command: ["/bin/sh", "-c", "sleep 5"]
{{- end }}
