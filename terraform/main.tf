terraform {
  required_providers {
    kind = {
      source  = "tehcyx/kind"
      version = "~> 0.11"
    }
  }
}

provider "kind" {}

resource "kind_cluster" "inception" {
  name           = "inception-tf"
  node_image     = "kindest/node:v1.37.0"
  wait_for_ready = false

  kind_config {
    kind        = "Cluster"
    api_version = "kind.x-k8s.io/v1alpha4"

    networking {
      disable_default_cni = true
    }

    node {
      role = "control-plane"

      extra_port_mappings {
        container_port = 80
        host_port      = 9080
        listen_address = "127.0.0.1"
        protocol       = "TCP"
      }

      extra_port_mappings {
        container_port = 443
        host_port      = 9443
        listen_address = "127.0.0.1"
        protocol       = "TCP"
      }
    }
  }
}
