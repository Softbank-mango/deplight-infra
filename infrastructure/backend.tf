terraform {
  backend "s3" {
    bucket         = "deplight-platform-tf-state"
    key            = "global/terraform.tfstate"
    region         = "ap-northeast-2"
    dynamodb_table = "deplight-platform-tf-locks"
    encrypt        = true
  }
}
