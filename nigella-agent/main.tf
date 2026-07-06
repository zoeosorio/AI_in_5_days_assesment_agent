terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

variable "project_id" {
  description = "The Google Cloud Project ID"
  type        = string
}

variable "region" {
  description = "The Google Cloud region"
  type        = string
  default     = "us-east1"
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# --- Enable Required APIs ---
resource "google_project_service" "services" {
  for_each = toset([
    "firestore.googleapis.com",
    "aiplatform.googleapis.com",
    "logging.googleapis.com",
    "cloudtrace.googleapis.com",
  ])
  service            = each.key
  disable_on_destroy = false
}

# --- Provision Firestore (Session & Catalog Store) ---
resource "google_firestore_database" "database" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"

  depends_on = [google_project_service.services["firestore.googleapis.com"]]
}

# --- Provision Service Account for the Agent ---
resource "google_service_account" "agent_sa" {
  account_id   = "nigella-agent-sa"
  display_name = "Nigella Cooking Agent Service Account"
  description  = "Service account used by the Nigella Cooking Agent to access Vertex AI and Cloud Logging."
}

# --- Assign IAM Roles to the Service Account ---
resource "google_project_iam_member" "vertex_ai_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.agent_sa.email}"
}

resource "google_project_iam_member" "firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  member  = "serviceAccount:${google_service_account.agent_sa.email}"
}

resource "google_project_iam_member" "logging_writer" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.agent_sa.email}"
}
