pipeline {
    agent any
    environment {
        AWS_REGION = 'ap-south-1'
        AWS_ACCOUNT_ID = '891612560902'
        BACKEND_REPO = 'fastapi-backend'
        FRONTEND_REPO = 'fastapi-frontend'
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
        stage('Build Backend Docker Image') {
            steps {
                script {
                    sh 'docker build -t backend-image -f Backend/Dockerfile .'
                    sh "docker tag backend-image:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${BACKEND_REPO}:${IMAGE_TAG}"
                }
            }
        }
        stage('Push Backend Docker Image') {
            steps {
                script {
                    sh "docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${BACKEND_REPO}:${IMAGE_TAG}"
                }
            }
        }
        stage('Build Frontend Docker Image') {
            steps {
                script {
                    sh 'docker build -t frontend-image ./Frontend'
                    sh "docker tag frontend-image:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${FRONTEND_REPO}:${IMAGE_TAG}"
                }
            }
        }
        stage('Push Frontend Docker Image') {
            steps {
                script {
                    sh "docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${FRONTEND_REPO}:${IMAGE_TAG}"
                }
            }
        }
    }
}
