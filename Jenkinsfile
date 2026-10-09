// Jenkins BUILD pipeline for ACEest Fitness & Gym.
// Requirements on the Jenkins agent: git, python3 (+venv), docker.
pipeline {
    agent any

    options {
        timestamps()
        timeout(time: 20, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    triggers {
        // Fallback to polling; a GitHub webhook (push) is the preferred trigger.
        pollSCM('H/5 * * * *')
    }

    environment {
        IMAGE = "aceest-fitness:${env.BUILD_NUMBER}"
    }

    stages {
        stage('Clean Workspace') {
            steps { deleteDir() }
        }

        stage('Checkout') {
            steps { checkout scm }
        }

        stage('Setup Python Env') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements-dev.txt
                '''
            }
        }

        stage('Lint') {
            steps {
                sh '. .venv/bin/activate && python -m compileall -q . && flake8 .'
            }
        }

        stage('Unit Tests') {
            steps {
                sh '. .venv/bin/activate && pytest --junitxml=test-results/junit.xml'
            }
            post {
                always { junit allowEmptyResults: true, testResults: 'test-results/junit.xml' }
            }
        }

        stage('Docker Build') {
            steps {
                sh '''
                    docker build --target runtime -t "$IMAGE" .
                    docker build --target test -t "$IMAGE-test" .
                '''
            }
        }

        stage('Tests in Container') {
            steps { sh 'docker run --rm "$IMAGE-test"' }
        }
    }

    post {
        always {
            sh 'docker rmi "$IMAGE-test" || true'
        }
        success { echo 'BUILD SUCCESS' }
        failure { echo 'BUILD FAILED' }
    }
}
