pipeline {
    agent any
    environment {
        AWS_REGION = 'ap-south-1'
        AWS_ACCOUNT_ID = '891612560902'
        BACKEND_REPO = 'fastapi-backend'
        FRONTEND_REPO = 'fastapi-frontend'
        DATABASE_REPO = 'fastapi-database'  // Add database repo
        IMAGE_TAG = 'latest'
    }
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        stage('Authenticate Docker to AWS ECR') {
            steps {
                withCredentials([aws(credentialsId: 'aws-credentials-id', region: AWS_REGION)]) {
                    script {
                        sh "aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
                    }
                }
            }
        }
        stage('Build Database Docker Image') {  // Add stage for building the database image
            steps {
                script {
                    sh 'docker build -t database-image -f Database/Dockerfile .'  // Build database image
                    sh "docker tag database-image:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${DATABASE_REPO}:${IMAGE_TAG}"  // Tag it for ECR
                }
            }
        }
        stage('Push Database Docker Image') {  // Add stage for pushing the database image
            steps {
                script {
                    sh "docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${DATABASE_REPO}:${IMAGE_TAG}"  // Push the database image
                }
            }
        }
        stage('Build Backend Docker Image') {
            steps {
                script {
                    sh 'docker build -t backend-image -f Backend/Dockerfile .'  // Build backend image
                    sh "docker tag backend-image:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${BACKEND_REPO}:${IMAGE_TAG}"  // Tag it for ECR
                }
            }
        }
        stage('Push Backend Docker Image') {
            steps {
                script {
                    sh "docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${BACKEND_REPO}:${IMAGE_TAG}"  // Push backend image
                }
            }
        }
        stage('Build Frontend Docker Image') {
            steps {
                script {
                    sh 'docker build -t frontend-image -f Frontend/Dockerfile .'  // Build frontend image
                    sh "docker tag frontend-image:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${FRONTEND_REPO}:${IMAGE_TAG}"  // Tag it for ECR
                }
            }
        }
        stage('Push Frontend Docker Image') {
            steps {
                script {
                    sh "docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${FRONTEND_REPO}:${IMAGE_TAG}"  // Push frontend image
                }
            }
        }
    }
}
