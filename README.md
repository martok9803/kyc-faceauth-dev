# KYC FaceAuth (Serverless Demo)

Personal experiment for building a **serverless face recognition / KYC verification system** on AWS — made with **Terraform**, **Lambda (Docker)**, **API Gateway**, **DynamoDB**, **S3**, and **Step Functions**.

---

### What it does, you asked yourself ?
- `/ping` – basic health check  
- `/echo` – test endpoint to write JSON to DynamoDB  
- `/presign-id` – get an S3 upload URL for an ID photo  
- `/liveness/start` – mock face liveness session (free version)  
- `/kyc/submit` – starts a fake KYC workflow via Step Functions  

Everything is deployed automatically through **GitHub Actions** (CI/CD) using **OIDC federation** — no local AWS keys needed (not sure if this is the best way, you can correct me)

---

###  Why I built it ?
Mostly to play with it:
- serverless architecture
- Terraform IaC for AWS
- Lambda + container deployment via ECR
- how CI/CD connects to cloud infrastructure

Also looks kinda cool on a resume ( or not ?)

---

###  Tech stack 
- **Terraform** for all AWS infra
- **AWS Lambda** (Python) packaged as Docker image
- **API Gateway HTTP API**
- **DynamoDB** + **S3** for session and file storage
- **Step Functions** (mock for now or forever idk)
- **GitHub Actions** for CI/CD

---

###  How to test
```bash
API="https://<your-api-id>.execute-api.eu-central-1.amazonaws.com"
curl "$API/ping"

