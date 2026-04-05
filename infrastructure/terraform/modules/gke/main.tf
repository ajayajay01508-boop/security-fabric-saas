variable "project_id"      { type = string }
variable "cluster_name"    { type = string }
variable "region"          { type = string }
variable "network"         { type = string; default = "default" }
variable "subnetwork"      { type = string; default = "default" }
variable "min_node_count"  { type = number; default = 1 }
variable "max_node_count"  { type = number; default = 10 }
variable "machine_type"    { type = string; default = "e2-standard-4" }
variable "tags"            { type = map(string); default = {} }

resource "google_container_cluster" "primary" {
  name                     = var.cluster_name
  location                 = var.region
  project                  = var.project_id
  remove_default_node_pool = true
  initial_node_count       = 1
  network                  = var.network
  subnetwork               = var.subnetwork

  release_channel { channel = "REGULAR" }

  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  ip_allocation_policy {}

  addons_config {
    http_load_balancing        { disabled = false }
    horizontal_pod_autoscaling { disabled = false }
    network_policy_config      { disabled = false }
  }

  network_policy {
    enabled  = true
    provider = "CALICO"
  }

  private_cluster_config {
    enable_private_nodes    = true
    enable_private_endpoint = false
    master_ipv4_cidr_block  = "172.16.0.0/28"
  }

  master_authorized_networks_config {
    cidr_blocks {
      cidr_block   = "0.0.0.0/0"
      display_name = "all"
    }
  }
}

resource "google_container_node_pool" "primary_nodes" {
  name       = "${var.cluster_name}-node-pool"
  location   = var.region
  cluster    = google_container_cluster.primary.name
  project    = var.project_id

  autoscaling {
    min_node_count = var.min_node_count
    max_node_count = var.max_node_count
  }

  management {
    auto_repair  = true
    auto_upgrade = true
  }

  node_config {
    preemptible  = false
    machine_type = var.machine_type
    disk_size_gb = 100
    disk_type    = "pd-ssd"

    workload_metadata_config { mode = "GKE_METADATA" }

    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform",
    ]

    labels = var.tags
  }
}

output "cluster_name"     { value = google_container_cluster.primary.name }
output "cluster_endpoint" { value = google_container_cluster.primary.endpoint }
output "cluster_ca"       { value = google_container_cluster.primary.master_auth[0].cluster_ca_certificate }
